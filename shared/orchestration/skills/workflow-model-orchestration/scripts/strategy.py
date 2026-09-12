#!/usr/bin/env python3
"""Build a bounded, read-only orchestration strategy from coordinator-authored JSON."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROLES = ("coordinator", "routine", "coder", "planner", "specialist")
_SPEC_FIELDS = {"tasks", "available_roles", "worker_limit", "repair"}
_TASK_FIELDS = {"id", "role", "depends_on", "reads", "writes", "check"}
_REPAIR_FIELDS = {"failed_node", "attempts", "cause"}
_MAPPING_FIELDS = {"model", "reasoning", "agent"}
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\Z")
_DRIVE = re.compile(r"[A-Za-z]:/")
_OPERATIONAL = ("permission", "outage", "credential", "capacity", "rate-limit", "authentication")


class ValidationError(ValueError):
    pass


def _object(value: Any, fields: set[str], required: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or not required.issubset(value) or not set(value).issubset(fields):
        raise ValidationError(f"{label} has missing or unknown fields")
    return value


def _text(value: Any, label: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum or "\0" in value:
        raise ValidationError(f"{label} must be a nonempty string of at most {maximum} characters")
    return value.strip()


def _path(value: Any, label: str) -> str:
    value = _text(value, label, 256).replace("\\", "/")
    parts = value.split("/")
    if value.startswith("/") or _DRIVE.match(value) or any(part in {"", ".", ".."} for part in parts):
        raise ValidationError(f"{label} must be a relative scope path")
    if any(any(ord(character) < 32 for character in part) for part in parts):
        raise ValidationError(f"{label} contains control characters")
    if any(character in value for character in ':*?[]') or any(part.endswith(('.', ' ')) for part in parts):
        raise ValidationError(f"{label} must be a literal scope without wildcard or platform aliases")
    return "/".join(parts)


def _string_list(value: Any, label: str, item_parser, maximum: int = 64) -> list[str]:
    if type(value) is not list or len(value) > maximum:
        raise ValidationError(f"{label} must be a list with at most {maximum} items")
    parsed = [item_parser(item, f"{label} item") for item in value]
    if len(parsed) != len(set(parsed)):
        raise ValidationError(f"{label} items must be unique")
    return parsed


def _role(value: Any, label: str) -> str:
    value = _text(value, label, 16)
    if value not in ROLES:
        raise ValidationError(f"{label} must be one of {', '.join(ROLES)}")
    return value


def _id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ValidationError(f"{label} must be a safe identifier of at most 64 characters")
    return value


def _mapping(value: Any) -> dict[str, dict[str, str]]:
    if type(value) is dict:
        value = {key: item for key, item in value.items() if key != '_promotion_history'}
    if type(value) is not dict or "coordinator" not in value or not set(value).issubset(ROLES):
        raise ValidationError("models must contain coordinator and only known roles")
    parsed: dict[str, dict[str, str]] = {}
    for role, entry in value.items():
        required = {"model", "reasoning"} | ({"agent"} if role != "coordinator" else set())
        entry = _object(entry, _MAPPING_FIELDS, required, f"models.{role}")
        item = {
            "model": _text(entry["model"], f"models.{role}.model", 128),
            "effort": _text(entry["reasoning"], f"models.{role}.reasoning", 32),
            "agent": _text(entry.get("agent", "coordinator"), f"models.{role}.agent", 64),
        }
        parsed[role] = item
    return parsed


def _validate(spec: Any) -> tuple[list[dict[str, Any]], list[str], int, dict[str, Any] | None]:
    spec = _object(spec, _SPEC_FIELDS, {"tasks", "available_roles", "worker_limit"}, "plan")
    raw_tasks = spec["tasks"]
    if type(raw_tasks) is not list or not 1 <= len(raw_tasks) <= 32:
        raise ValidationError("tasks must contain between 1 and 32 nodes")

    tasks: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_tasks):
        raw = _object(raw, _TASK_FIELDS, _TASK_FIELDS, f"tasks[{index}]")
        tasks.append({
            "id": _id(raw["id"], f"tasks[{index}].id"),
            "role": _role(raw["role"], f"tasks[{index}].role"),
            "depends_on": _string_list(raw["depends_on"], f"tasks[{index}].depends_on", _id, 32),
            "reads": _string_list(raw["reads"], f"tasks[{index}].reads", _path),
            "writes": _string_list(raw["writes"], f"tasks[{index}].writes", _path),
            "check": _text(raw["check"], f"tasks[{index}].check", 512),
        })

    ids = [task["id"] for task in tasks]
    if len(ids) != len(set(ids)):
        raise ValidationError("task ids must be unique")
    known = set(ids)
    for task in tasks:
        unknown = set(task["depends_on"]) - known
        if unknown:
            raise ValidationError(f"task {task['id']} has unknown dependencies: {', '.join(sorted(unknown))}")
        if task["id"] in task["depends_on"]:
            raise ValidationError(f"task {task['id']} cannot depend on itself")

    available = _string_list(spec["available_roles"], "available_roles", _role, len(ROLES))
    worker_limit = spec["worker_limit"]
    if type(worker_limit) is not int or not 0 <= worker_limit <= 2:
        raise ValidationError("worker_limit must be an integer from 0 to 2")

    repair = spec.get("repair")
    if repair is not None:
        repair = _object(repair, _REPAIR_FIELDS, _REPAIR_FIELDS, "repair")
        repair = {
            "failed_node": _id(repair["failed_node"], "repair.failed_node"),
            "attempts": repair["attempts"],
            "cause": _text(repair["cause"], "repair.cause", 256),
        }
        if repair["failed_node"] not in known:
            raise ValidationError("repair.failed_node must name a task")
        if type(repair["attempts"]) is not int or not 0 <= repair["attempts"] <= 1000:
            raise ValidationError("repair.attempts must be an integer from 0 to 1000")
    return tasks, available, worker_limit, repair


def _topological(ids: list[str], dependencies: dict[str, set[str]]) -> list[str]:
    remaining = {node: set(dependencies[node]) for node in ids}
    ordered: list[str] = []
    while remaining:
        ready = [node for node in ids if node in remaining and not remaining[node]]
        if not ready:
            raise ValidationError("task dependencies contain a cycle")
        ordered.extend(ready)
        for node in ready:
            del remaining[node]
        for value in remaining.values():
            value.difference_update(ready)
    return ordered


def _precedes(source: str, target: str, dependencies: dict[str, set[str]]) -> bool:
    pending = list(dependencies[target])
    seen: set[str] = set()
    while pending:
        node = pending.pop()
        if node == source:
            return True
        if node not in seen:
            seen.add(node)
            pending.extend(dependencies[node])
    return False


def _path_overlap(left: str, right: str) -> bool:
    # Conservative on case-sensitive hosts too; Windows aliases must never run concurrently.
    left, right = left.casefold(), right.casefold()
    return left == right or left.startswith(right + "/") or right.startswith(left + "/")


def _conflict(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return any(
        _path_overlap(write, path)
        for write in left["writes"]
        for path in right["reads"] + right["writes"]
    ) or any(
        _path_overlap(write, path)
        for write in right["writes"]
        for path in left["reads"] + left["writes"]
    )


def _loop(repair: dict[str, Any] | None) -> dict[str, Any]:
    if repair is None:
        return {"decision": "none", "node": None, "reason": "no failed node"}
    cause = repair["cause"].lower().replace("_", "-").replace(" ", "-")
    if "external-effect" in cause and ("uncertain" in cause or "unknown" in cause):
        return {"decision": "reconcile", "node": repair["failed_node"], "reason": "external effect is uncertain; reconcile before retry"}
    if any(marker in cause for marker in _OPERATIONAL):
        return {"decision": "blocked", "node": repair["failed_node"], "reason": "operational cause requires resolution, not a stronger model"}
    if repair["attempts"] == 0:
        return {"decision": "retry", "node": repair["failed_node"], "reason": "one targeted retry is available"}
    return {"decision": "replan", "node": repair["failed_node"], "reason": "targeted retry limit reached"}


def plan(spec: Any, mapping: Any) -> dict[str, Any]:
    """Validate a task graph and return a bounded schedule without dispatching it."""
    tasks, available, worker_limit, repair = _validate(spec)
    models = _mapping(mapping)
    ids = [task["id"] for task in tasks]
    by_id = {task["id"]: task for task in tasks}
    dependencies = {task["id"]: set(task["depends_on"]) for task in tasks}
    _topological(ids, dependencies)

    serialized: list[tuple[str, str]] = []
    for index, left in enumerate(tasks):
        for right in tasks[index + 1:]:
            if _conflict(left, right) and not _precedes(left["id"], right["id"], dependencies) and not _precedes(right["id"], left["id"], dependencies):
                dependencies[right["id"]].add(left["id"])
                serialized.append((left["id"], right["id"]))
    _topological(ids, dependencies)

    assignments: dict[str, dict[str, Any]] = {}
    for task in tasks:
        requested = task["role"]
        reason = None
        effective = requested
        if requested != "coordinator":
            if worker_limit == 0:
                reason = "worker_limit is 0; routed to coordinator"
            elif requested not in available:
                reason = f"{requested} is not in available_roles; routed to coordinator"
            elif requested not in models:
                reason = f"{requested} has no configured mapping; routed to coordinator"
            if reason:
                effective = "coordinator"
        configured = models[effective]
        assignments[task["id"]] = {
            "requested_role": requested,
            "effective_role": effective,
            "model": configured["model"],
            "effort": configured["effort"],
            "agent": configured["agent"],
            "reason": reason,
        }

    remaining = set(ids)
    completed: set[str] = set()
    waves: list[list[str]] = []
    while remaining:
        ready = [node for node in ids if node in remaining and dependencies[node] <= completed]
        exclusive = next((node for node in ready if by_id[node]["role"] in {"planner", "specialist"}), None)
        if exclusive:
            selected = [exclusive]
        else:
            coordinators = [node for node in ready if assignments[node]["effective_role"] == "coordinator"]
            workers = [node for node in ready if assignments[node]["effective_role"] != "coordinator"]
            selected = coordinators[:1] + workers[:worker_limit]
        if not selected:  # Defensive: validation and the DAG guarantee at least one ready node.
            raise ValidationError("task graph cannot be scheduled")
        waves.append(selected)
        completed.update(selected)
        remaining.difference_update(selected)

    has_edges = any(dependencies.values())
    if len(tasks) == 1:
        strategy = "direct"
    elif has_edges:
        strategy = "task_graph"
    elif any(sum(assignments[node]["effective_role"] != "coordinator" for node in wave) > 1 for wave in waves):
        strategy = "bounded_swarm"
    else:
        strategy = "sequential"

    rationale = [
        f"caller-declared roles control delegation; worker concurrency is capped at {worker_limit}",
        "planner and specialist nodes receive exclusive waves",
    ]
    rationale.extend(f"serialized {left} before {right} because their scopes overlap" for left, right in serialized)
    return {
        "notice": "Proposal only; model fields are configured assignments, not observed runtime selection or dispatch.",
        "strategy": strategy,
        "waves": waves,
        "assignments": assignments,
        "rationale": rationale,
        "loop": _loop(repair),
    }


def _load(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle, parse_constant=lambda _value: (_ for _ in ()).throw(ValueError()))


def _catalog_freshness(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"status": "unknown", "verified_at": None}
    try:
        catalog = _load(path)
        catalog = _object(catalog, {"schema_version", "verified_at", "sources", "models", "notice"}, {"schema_version", "verified_at", "sources", "models", "notice"}, "model catalog")
        if catalog["schema_version"] != 1:
            raise ValidationError("unsupported model catalog schema")
        verified = datetime.fromisoformat(_text(catalog["verified_at"], "model catalog verified_at", 64).replace("Z", "+00:00"))
        if verified.tzinfo is None or verified.utcoffset() is None:
            raise ValueError
        age = max(0.0, (datetime.now(timezone.utc) - verified.astimezone(timezone.utc)).total_seconds() / 3600)
        return {
            "status": "current" if age <= 24 else "source_refresh_due",
            "verified_at": verified.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, ValidationError):
        return {"status": "unknown", "verified_at": None}


def context(home: Path) -> dict[str, Any]:
    """Read configured role assignments and catalog freshness from a Codex home."""
    models_path = home / "model-routing" / "models.json"
    try:
        configured = _mapping(_load(models_path)) if models_path.is_file() else None
        roles = ({role: {"model": value["model"], "reasoning": value["effort"]} for role, value in configured.items()}
                 if configured is not None else None)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, ValidationError):
        roles = None
    return {
        "roles_status": "configured" if roles is not None else "unknown",
        "roles": roles or {},
        "model_catalog": _catalog_freshness(home / "model-routing" / "model-catalog.json"),
        "rules": [
            "direct for one small node",
            "bounded_swarm for independent bounded workers",
            "task_graph for dependencies or overlapping scopes",
            "retry only the failed check once; then replan",
        ],
    }


def _json(value: str) -> Any:
    try:
        if not value.lstrip().startswith(('{', '[')):
            return _load(Path(value))
        return json.loads(value, parse_constant=lambda _value: (_ for _ in ()).throw(ValueError()))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise argparse.ArgumentTypeError("value must be valid JSON or a readable JSON file") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--plan", type=_json, help="coordinator-authored plan JSON file or object")
    mode.add_argument("--context", action="store_true", help="show local routing context")
    parser.add_argument("--models", type=_json, help="role mapping JSON file or object for --plan")
    parser.add_argument("--home", type=Path, help="Codex home for --context")
    args = parser.parse_args(argv)
    try:
        if args.plan is not None:
            if args.models is None:
                raise ValidationError("--models is required with --plan")
            result = plan(args.plan, args.models)
        else:
            if args.home is None:
                raise ValidationError("--home is required with --context")
            result = context(args.home)
    except ValidationError as exc:
        print(json.dumps({"error": str(exc)}, separators=(",", ":")), file=sys.stderr)
        return 2
    print(json.dumps(result, separators=(",", ":"), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
