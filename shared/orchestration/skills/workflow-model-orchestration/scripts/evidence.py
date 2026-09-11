#!/usr/bin/env python3
"""Read-only mechanical verification for orchestration artifacts and outcomes."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tomllib
from collections import deque
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any


_HEX64 = re.compile(r"[0-9a-fA-F]{64}\Z")
_GIT_OBJECT_ID = re.compile(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})\Z")
_MANIFEST_FIELDS = {"root", "files", "git_scope"}
_FILE_FIELDS = {"path", "sha256", "format"}
_GIT_FIELDS = {"base", "allowed"}
_OUTCOME_FIELDS = {
    "schema_version",
    "date",
    "utc",
    "category",
    "outcome",
    "coordinator_model",
    "worker_models",
    "rework_cycles",
    "escalation_reason",
    "verification",
    "incompatibility",
}


class ValidationError(ValueError):
    pass


def _emit(value: dict[str, Any]) -> None:
    print(json.dumps(value, separators=(",", ":"), ensure_ascii=False))


def _load_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(
                handle,
                parse_constant=lambda _value: (_ for _ in ()).throw(ValueError()),
            )
    except (OSError, UnicodeError) as exc:
        raise ValidationError("cannot read JSON file") from exc
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValidationError("invalid JSON") from exc


def _relative_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or "\0" in value:
        raise ValidationError(f"{label} must be a nonempty relative path")
    parts = value.replace("\\", "/").split("/")
    candidate = Path(value)
    if candidate.is_absolute() or candidate.drive or any(part in {"", ".", ".."} for part in parts):
        raise ValidationError(f"{label} must remain under root")
    return "/".join(parts)


def _inside_root(root: Path, relative: str) -> Path:
    target = root.joinpath(*relative.split("/"))
    try:
        resolved = target.resolve(strict=True)
    except (OSError, RuntimeError, ValueError) as exc:
        raise ValidationError("file is missing or inaccessible") from exc
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValidationError("file resolves outside root") from exc
    if not resolved.is_file():
        raise ValidationError("path is not a regular file")
    return resolved


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _syntax_check(path: Path, file_format: str) -> None:
    try:
        if file_format == "json":
            _load_json(path)
        else:
            with path.open("rb") as handle:
                tomllib.load(handle)
    except ValidationError:
        raise
    except (OSError, UnicodeError) as exc:
        raise ValidationError("cannot read file") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ValidationError("invalid TOML") from exc


def _git(root: Path, *args: str) -> bytes:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ValidationError("git command failed") from exc
    return completed.stdout


def _git_scope(root: Path, scope: Any) -> list[str]:
    if type(scope) is not dict or set(scope) != _GIT_FIELDS:
        raise ValidationError("git_scope must contain only base and allowed")
    base = scope["base"]
    allowed_raw = scope["allowed"]
    if not isinstance(base, str) or not base or "\0" in base or "\n" in base or "\r" in base:
        raise ValidationError("git_scope base must be a nonempty ref")
    if type(allowed_raw) is not list:
        raise ValidationError("git_scope allowed must be a list")
    allowed = {_relative_path(item, "allowed path") for item in allowed_raw}
    if len(allowed) != len(allowed_raw):
        raise ValidationError("git_scope allowed paths must be unique")

    repository = Path(_git(root, "rev-parse", "--show-toplevel").decode("utf-8").strip()).resolve()
    if repository != root:
        raise ValidationError("root must be the repository root")
    commit = _git(root, "rev-parse", "--verify", "--end-of-options", f"{base}^{{commit}}").decode("ascii").strip()
    if not _GIT_OBJECT_ID.fullmatch(commit):
        raise ValidationError("git base did not resolve to a commit")

    staged = _git(root, "diff", "--cached", "--no-renames", "--no-ext-diff", "--no-textconv", "--name-only", "-z", commit, "--")
    tracked = _git(root, "diff", "--no-renames", "--no-ext-diff", "--no-textconv", "--name-only", "-z", commit, "--")
    untracked = _git(root, "ls-files", "--others", "--exclude-standard", "-z")
    changed = {
        item.decode("utf-8", errors="surrogateescape")
        for item in (staged + tracked + untracked).split(b"\0")
        if item
    }
    return sorted(changed - allowed)


def verify(manifest_path: Path) -> dict[str, Any]:
    failures: list[dict[str, str]] = []
    checks = 0
    try:
        manifest = _load_json(manifest_path)
        if type(manifest) is not dict or not set(manifest).issubset(_MANIFEST_FIELDS):
            raise ValidationError("manifest has invalid or unknown fields")
        if "root" not in manifest or "files" not in manifest:
            raise ValidationError("manifest requires root and files")
        root_value = manifest["root"]
        if not isinstance(root_value, str) or not root_value:
            raise ValidationError("root must be an absolute path")
        root_path = Path(root_value)
        if not root_path.is_absolute():
            raise ValidationError("root must be an absolute path")
        try:
            root = root_path.resolve(strict=True)
        except (OSError, RuntimeError, ValueError) as exc:
            raise ValidationError("root is missing or inaccessible") from exc
        if not root.is_dir():
            raise ValidationError("root must be a directory")

        files = manifest["files"]
        if type(files) is not list or not files:
            raise ValidationError("files must be a nonempty list")
        seen: set[str] = set()
        for entry in files:
            checks += 1
            try:
                if type(entry) is not dict or not {"path", "sha256"}.issubset(entry) or not set(entry).issubset(_FILE_FIELDS):
                    raise ValidationError("file entry has invalid or unknown fields")
                relative = _relative_path(entry["path"], "file path")
                if relative in seen:
                    raise ValidationError("file paths must be unique")
                seen.add(relative)
                expected = entry["sha256"]
                if not isinstance(expected, str) or not _HEX64.fullmatch(expected):
                    raise ValidationError("sha256 must be 64 hexadecimal characters")
                file_format = entry.get("format")
                if file_format is not None and (not isinstance(file_format, str) or file_format not in {"json", "toml"}):
                    raise ValidationError("format must be json or toml")
                target = _inside_root(root, relative)
                if _sha256(target).lower() != expected.lower():
                    raise ValidationError("sha256 mismatch")
                if file_format:
                    checks += 1
                    _syntax_check(target, file_format)
            except (OSError, ValidationError) as exc:
                failures.append({"check": "file", "path": entry.get("path", "<invalid>") if type(entry) is dict else "<invalid>", "error": str(exc)})

        if "git_scope" in manifest:
            checks += 1
            try:
                outside = _git_scope(root, manifest["git_scope"])
                if outside:
                    failures.append({"check": "git_scope", "error": "changed paths outside allowed scope", "paths": outside})
            except (OSError, UnicodeError, ValidationError) as exc:
                failures.append({"check": "git_scope", "error": str(exc)})
    except ValidationError as exc:
        failures.append({"check": "manifest", "error": str(exc)})

    return {"passed": not failures, "checks": checks, "failures": failures}


def _utc(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise ValidationError("timestamp must be a nonempty string")
    try:
        if "T" not in value and " " not in value:
            parsed = datetime.combine(date.fromisoformat(value), time(), timezone.utc)
        else:
            parsed = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
            if parsed.tzinfo is None or parsed.utcoffset() is None:
                raise ValueError
    except ValueError as exc:
        raise ValidationError("timestamp must be an ISO date or timezone-aware datetime") from exc
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _nullable_string(value: Any, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be a string or null")
    return value


def _outcome(record: Any) -> dict[str, Any]:
    if type(record) is not dict or not set(record).issubset(_OUTCOME_FIELDS):
        raise ValidationError("record has invalid or unknown fields")
    timestamps = [field for field in ("utc", "date") if field in record]
    if len(timestamps) != 1:
        raise ValidationError("record requires exactly one of utc or date")
    required = {
        "category",
        "outcome",
        "worker_models",
        "rework_cycles",
        "escalation_reason",
        "verification",
        "incompatibility",
    }
    if not required.issubset(record):
        raise ValidationError("record is missing required fields")
    if "schema_version" in record and "coordinator_model" not in record:
        raise ValidationError("record is missing required fields")
    if record.get("schema_version", 1) != 1 or type(record.get("schema_version", 1)) is not int:
        raise ValidationError("schema_version must be 1")
    category = record["category"]
    if not isinstance(category, str) or not category:
        raise ValidationError("category must be a nonempty string")
    outcome = record["outcome"]
    if not isinstance(outcome, str) or outcome not in {"verified", "partial", "blocked"}:
        raise ValidationError("outcome must be verified, partial, or blocked")
    workers = record["worker_models"]
    if type(workers) is not list or any(item is not None and not isinstance(item, str) for item in workers):
        raise ValidationError("worker_models must be a list of strings or nulls")
    cycles = record["rework_cycles"]
    if type(cycles) is not int or cycles < 0:
        raise ValidationError("rework_cycles must be a nonnegative integer")
    verification = record["verification"]
    if type(verification) is list:
        if any(not isinstance(item, str) for item in verification):
            raise ValidationError("verification list must contain only strings")
        verification = "; ".join(verification)
    if not isinstance(verification, str):
        raise ValidationError("verification must be a string or list of strings")
    return {
        "schema_version": 1,
        "utc": _utc(record[timestamps[0]]),
        "category": category,
        "outcome": outcome,
        "coordinator_model": _nullable_string(record.get("coordinator_model"), "coordinator_model"),
        "worker_models": workers,
        "rework_cycles": cycles,
        "escalation_reason": _nullable_string(record["escalation_reason"], "escalation_reason"),
        "verification": verification,
        "incompatibility": _nullable_string(record["incompatibility"], "incompatibility"),
    }


def outcomes(path: Path, limit: int) -> dict[str, Any]:
    recent: deque[tuple[int, bytes]] = deque(maxlen=limit)
    errors: list[dict[str, Any]] = []
    try:
        with path.open("rb") as handle:
            for line_number, line in enumerate(handle, 1):
                if line.strip():
                    recent.append((line_number, line))
    except OSError:
        return {"passed": False, "records": [], "errors": [{"error": "cannot read outcomes file"}]}

    records = []
    for line_number, raw in recent:
        try:
            parsed = json.loads(
                raw.decode("utf-8"),
                parse_constant=lambda _value: (_ for _ in ()).throw(ValueError()),
            )
            records.append(_outcome(parsed))
        except (UnicodeError, json.JSONDecodeError, ValueError, ValidationError):
            errors.append({"line": line_number, "error": "invalid outcome record"})
    return {"passed": not errors, "records": records, "errors": errors}


def _limit(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("limit must be an integer") from exc
    if not 1 <= parsed <= 10_000:
        raise argparse.ArgumentTypeError("limit must be between 1 and 10000")
    return parsed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    verify_parser = commands.add_parser("verify", help="verify a mechanical evidence manifest")
    verify_parser.add_argument("--manifest", type=Path, required=True)
    outcomes_parser = commands.add_parser("outcomes", help="normalize recent outcome records")
    outcomes_parser.add_argument("--path", type=Path, required=True)
    outcomes_parser.add_argument("--limit", type=_limit, default=100)
    args = parser.parse_args(argv)

    result = verify(args.manifest) if args.command == "verify" else outcomes(args.path, args.limit)
    _emit(result)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
