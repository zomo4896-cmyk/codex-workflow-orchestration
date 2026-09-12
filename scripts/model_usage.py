#!/usr/bin/env python3
"""Read local Codex rollout records and summarize model usage without modifying them."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


COUNTERS = (
    "input_tokens",
    "cached_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
    "total_tokens",
)
CACHE_VERSION = 1


def _number(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        value = int(value)
    except (TypeError, ValueError):
        return None
    return value if value >= 0 else None


def _activity(source: Any) -> str:
    if source is None:
        return "unknown"
    text = json.dumps(source, sort_keys=True).lower() if isinstance(source, dict) else str(source).lower()
    if "subagent" in text or "thread_spawn" in text:
        return "worker"
    if any(word in text for word in ("automation", "scheduled", "schedule", "cron", "heartbeat")):
        return "automation"
    return "interactive"


def _context(payload: dict[str, Any], fallback: tuple[str, str]) -> tuple[str, str]:
    return str(payload.get("model") or fallback[0] or "unknown"), str(
        payload.get("effort") or fallback[1] or "unknown"
    )


def _response(
    event: dict[str, Any],
    activity: str,
    usage: Any,
    *,
    legacy: bool = False,
    uncertain: bool = False,
) -> dict[str, Any]:
    payload = event["payload"]
    response_id = payload.get("response_id")
    return {
        "model": event["context"][0],
        "effort": event["context"][1],
        "activity": activity,
        "usage": {
            name: value
            for name in COUNTERS
            if (value := _number(usage.get(name) if isinstance(usage, dict) else None)) is not None
        },
        "missing_usage": not isinstance(usage, dict),
        "missing_response_id": response_id is None and not legacy,
        "legacy": legacy,
        "uncertain": uncertain,
        "timestamp": event["timestamp"] if isinstance(event["timestamp"], str) else None,
        "line": event["line"],
        "turn_key": event["turn_key"],
        "response_hash": (
            hashlib.sha256(str(response_id).encode("utf-8")).hexdigest() if response_id is not None else None
        ),
    }


def _legacy_responses(events: list[dict[str, Any]], activity: str, explicit_turns: set[str]) -> list[dict[str, Any]]:
    responses: list[dict[str, Any]] = []
    previous_total: dict[str, int] | None = None
    for event in events:
        info = event["payload"].get("info")
        info = info if isinstance(info, dict) else {}
        usage = info.get("last_token_usage")
        raw_total = info.get("total_token_usage")
        total = {
            name: value
            for name in COUNTERS
            if (value := _number(raw_total.get(name) if isinstance(raw_total, dict) else None)) is not None
        }
        duplicate = bool(total) and previous_total == total
        uncertain = not total
        if total and previous_total and not duplicate:
            common = total.keys() & previous_total.keys()
            if any(total[name] < previous_total[name] for name in common):
                uncertain = True
            elif isinstance(usage, dict):
                for name in common:
                    last = _number(usage.get(name))
                    if last is not None and total[name] - previous_total[name] != last:
                        uncertain = True
                        break
        if total:
            previous_total = total
        if duplicate or event["turn_key"] in explicit_turns:
            continue
        responses.append(
            _response(
                event,
                activity,
                usage,
                legacy=True,
                uncertain=uncertain or not isinstance(usage, dict),
            )
        )
    return responses


def _parse_file(path: Path) -> tuple[dict[str, Any], bool]:
    source: Any = None
    current = ("unknown", "unknown")
    current_turn = "before-context"
    context_number = 0
    turns: dict[str, tuple[str, str]] = {}
    explicit: dict[str, dict[str, Any]] = {}
    legacy: list[dict[str, Any]] = []
    malformed_lines = 0
    unreadable = False
    try:
        stream = path.open(encoding="utf-8", errors="replace")
    except OSError:
        return {"responses": [], "malformed_lines": 0}, True

    try:
        with stream:
            for line_number, line in enumerate(stream, 1):
                try:
                    item = json.loads(line)
                except (json.JSONDecodeError, TypeError):
                    malformed_lines += 1
                    continue
                if not isinstance(item, dict):
                    continue
                payload = item.get("payload")
                payload = payload if isinstance(payload, dict) else {}
                record_type = item.get("type")
                if record_type == "session_meta":
                    source = {"source": payload.get("source"), "thread_source": payload.get("thread_source")} if payload.get("source") is not None or payload.get("thread_source") is not None else None
                    continue
                if record_type == "turn_context":
                    context_number += 1
                    current = _context(payload, current)
                    turn_id = payload.get("turn_id") or payload.get("root_turn_id")
                    current_turn = str(turn_id) if turn_id is not None else f"context:{context_number}"
                    for name in ("turn_id", "root_turn_id"):
                        value = payload.get(name)
                        if value is not None:
                            turns[str(value)] = current
                    continue
                if record_type not in ("token_usage_record", "event_msg"):
                    continue
                if record_type == "event_msg" and payload.get("type") != "token_count":
                    continue
                turn_id = payload.get("turn_id") or payload.get("root_turn_id")
                turn_key = str(turn_id) if turn_id is not None else current_turn
                event = {
                    "payload": payload,
                    "context": turns.get(turn_key, current),
                    "turn_key": turn_key,
                    "timestamp": item.get("timestamp"),
                    "line": line_number,
                }
                if record_type == "token_usage_record":
                    response_id = payload.get("response_id")
                    key = str(response_id) if response_id is not None else f"line:{line_number}"
                    explicit[key] = event
                else:
                    legacy.append(event)
    except OSError:
        unreadable = True

    activity = _activity(source)
    responses = [
        _response(event, activity, event["payload"].get("usage"))
        for event in explicit.values()
        if isinstance(event["payload"].get("usage"), dict)
    ]
    explicit_turns = {event["turn_key"] for event in explicit.values() if isinstance(event["payload"].get("usage"), dict)}
    legacy_responses = _legacy_responses(legacy, activity, explicit_turns)
    responses.extend(legacy_responses)
    covered_turns = explicit_turns | {event["turn_key"] for event in legacy_responses}
    responses.extend(
        _response(event, activity, None)
        for event in explicit.values()
        if not isinstance(event["payload"].get("usage"), dict) and event["turn_key"] not in covered_turns
    )
    for response in responses:
        response.pop("turn_key", None)
    return {"responses": responses, "malformed_lines": malformed_lines}, unreadable


def _new_row(model: str, effort: str, activity: str) -> dict[str, Any]:
    row: dict[str, Any] = {
        "model": model,
        "effort": effort,
        "activity": activity,
        "responses": 0,
        "missing_usage_responses": 0,
        "missing_response_id": 0,
        "legacy_estimated_responses": 0,
        "legacy_uncertain_responses": 0,
        "session_count": 0,
        "first_seen": None,
        "last_seen": None,
    }
    for counter in COUNTERS:
        row[counter] = None
        row[f"{counter}_missing"] = 0
    return row


def _add_response(row: dict[str, Any], response: dict[str, Any]) -> None:
    row["responses"] += 1
    row["missing_usage_responses"] += int(response["missing_usage"])
    row["missing_response_id"] += int(response["missing_response_id"])
    row["legacy_estimated_responses"] += int(response["legacy"])
    row["legacy_uncertain_responses"] += int(response["uncertain"])
    usage = response["usage"]
    for counter in COUNTERS:
        if counter not in usage:
            row[f"{counter}_missing"] += 1
        else:
            row[counter] = (row[counter] or 0) + usage[counter]
    timestamp = response["timestamp"]
    if timestamp is not None:
        row["first_seen"] = timestamp if row["first_seen"] is None else min(row["first_seen"], timestamp)
        row["last_seen"] = timestamp if row["last_seen"] is None else max(row["last_seen"], timestamp)


def _load_cache(cache_path: Path | None) -> dict[str, Any]:
    if cache_path is None:
        return {}
    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return {}
    return cache.get("files", {}) if cache.get("version") == CACHE_VERSION else {}


def _write_cache(cache_path: Path | None, files: dict[str, Any]) -> None:
    if cache_path is None:
        return
    temporary: Path | None = None
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = cache_path.with_name(f".{cache_path.name}.{os.getpid()}.tmp")
        temporary.write_text(json.dumps({"version": CACHE_VERSION, "files": files}), encoding="utf-8")
        temporary.replace(cache_path)
    except OSError:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def _mtime(path: Path) -> int:
    try:
        return path.stat().st_mtime_ns
    except OSError:
        return 0


def _paths(sessions: Path, limit: int | None = None) -> list[Path]:
    try:
        paths = list(sessions.rglob("rollout-*.jsonl"))
    except OSError:
        return []
    paths.sort(key=_mtime, reverse=True)
    return paths if limit is None else paths[: max(limit, 0)]


def _collect(
    sessions: Path, paths: list[Path], cache_path: Path | None = None
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    cached_files = _load_cache(cache_path)
    next_cache: dict[str, Any] = {}
    selected: dict[str, tuple[tuple[str, int, int], dict[str, Any]]] = {}
    malformed_lines = unreadable_files = cache_hits = duplicate_responses = 0

    for path in paths:
        try:
            stat = path.stat()
            relative = str(path.relative_to(sessions))
        except (OSError, ValueError):
            unreadable_files += 1
            continue
        signature = {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns}
        cached = cached_files.get(relative)
        if (
            isinstance(cached, dict)
            and all(cached.get(name) == value for name, value in signature.items())
            and isinstance(cached.get("parsed"), dict)
            and isinstance(cached["parsed"].get("responses"), list)
        ):
            parsed = cached["parsed"]
            unreadable = False
            cache_hits += 1
        else:
            parsed, unreadable = _parse_file(path)
            unreadable_files += int(unreadable)
        # Refresh the tiny header even on cache hits so older caches recover thread_source classification.
        if not unreadable:
            try:
                with path.open(encoding="utf-8") as stream:
                    header = json.loads(stream.readline())
                if header.get("type") == "session_meta":
                    meta = header.get("payload") or {}
                    source = {"source": meta.get("source"), "thread_source": meta.get("thread_source")} if meta.get("source") is not None or meta.get("thread_source") is not None else None
                    for response in parsed.get("responses", []):
                        response["activity"] = _activity(source)
            except (OSError, UnicodeError, ValueError, AttributeError):
                pass  # Full-parser/cache coverage remains authoritative if a header cannot be decoded.
        if not unreadable:
            next_cache[relative] = {**signature, "parsed": parsed}
        malformed_lines += int(parsed.get("malformed_lines") or 0)
        for response in parsed.get("responses", []):
            if not isinstance(response, dict):
                continue
            response = dict(response)
            response["session"] = relative
            response_hash = response.get("response_hash")
            key = f"response:{response_hash}" if response_hash else f"record:{relative}:{response.get('line')}"
            order = (response.get("timestamp") or "", stat.st_mtime_ns, int(response.get("line") or 0))
            if key in selected:
                duplicate_responses += 1
            if key not in selected or order >= selected[key][0]:
                selected[key] = (order, response)

    _write_cache(cache_path, next_cache)
    return [value[1] for value in selected.values()], {
        "unreadable_files": unreadable_files,
        "malformed_lines": malformed_lines,
        "cache_hits": cache_hits,
        "duplicate_response_records": duplicate_responses,
    }


def inventory(sessions: Path, cache_path: Path | None = None) -> dict[str, Any]:
    """Inventory all local rollout files, including sessions still being written."""
    sessions = Path(sessions)
    paths = _paths(sessions)
    responses, coverage = _collect(sessions, paths, cache_path)
    totals: dict[tuple[str, str, str], dict[str, Any]] = {}
    row_sessions: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for response in responses:
        key = (
            str(response.get("model") or "unknown"),
            str(response.get("effort") or "unknown"),
            str(response.get("activity") or "unknown"),
        )
        row = totals.setdefault(key, _new_row(*key))
        _add_response(row, response)
        row_sessions[key].add(response["session"])
    for key, row in totals.items():
        row["session_count"] = len(row_sessions[key])
    coverage.update(
        {
            "scanned_files": len(paths),
            "scope": "all local rollout-*.jsonl files, including ongoing sessions",
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
    )
    return {"models": [totals[key] for key in sorted(totals)], "coverage": coverage}


def records(path: Path):
    """Yield the legacy summary tuple for each response in one rollout file."""
    parsed, _ = _parse_file(path)
    for response in parsed["responses"]:
        yield response["model"], response["usage"].get("total_tokens", 0), response["usage"].get(
            "reasoning_output_tokens", 0
        )


def summarize(sessions: Path, limit: int) -> dict[str, tuple[int, int, int]]:
    sessions = Path(sessions)
    responses, _ = _collect(sessions, _paths(sessions, limit))
    totals = defaultdict(lambda: [0, 0, 0])
    for response in responses:
        row = totals[response["model"]]
        row[0] += 1
        row[1] += response["usage"].get("total_tokens", 0)
        row[2] += response["usage"].get("reasoning_output_tokens", 0)
    return {model: tuple(values) for model, values in totals.items()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sessions", type=Path, default=Path.home() / ".codex" / "sessions")
    parser.add_argument("--latest", type=int, default=100, help="number of recent rollout files to inspect")
    parser.add_argument("--inventory", action="store_true", help="emit the complete local inventory as JSON")
    parser.add_argument("--cache", type=Path, help="optional private inventory cache path")
    args = parser.parse_args()
    if args.inventory:
        print(json.dumps(inventory(args.sessions, args.cache), indent=2))
        return
    print("model\tresponses\ttotal_tokens\treasoning_tokens")
    for model, (responses, tokens, reasoning) in sorted(summarize(args.sessions, args.latest).items()):
        print(f"{model}\t{responses}\t{tokens}\t{reasoning}")


if __name__ == "__main__":
    main()
