#!/usr/bin/env python3
"""Install the small, portable Codex shared setup without touching unrelated settings."""
from __future__ import annotations

import argparse
import copy
from contextlib import contextmanager
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SHARED = ROOT / "shared"
BEGIN = "<!-- BEGIN:global-"
END = "<!-- END:global-"
COMPONENTS = ("adhd", "orchestration")
COMPONENT = {
    "adhd": {
        "blocks": ("global-adhd-creative-design-agent",),
        "resources": (
            "skills/adhd-creative-design-agent/SKILL.md", "skills/adhd-creative-design-agent/agents/openai.yaml",
            "skills/adhd-creative-flow/SKILL.md", "skills/adhd-creative-flow/agents/openai.yaml",
            "skills/adhd-creative-flow/references/creative-direction.md", "skills/adhd-creative-flow/references/logo-craft.md",
            "skills/adhd-creative-flow/scripts/validate_svg.py",
        ),
    },
    "orchestration": {
        "blocks": ("global-model-orchestration",),
        "resources": (
            "models.json", "REVIEW.md", "agents/quota_routine.toml", "agents/quota_planner.toml", "agents/quota_coder.toml", "agents/quota_specialist.toml",
            "skills/workflow-model-orchestration/SKILL.md", "skills/workflow-model-orchestration/agents/openai.yaml",
        ),
    },
}


class SyncError(RuntimeError): pass


ROLE_CANDIDATES = {
    'coordinator': [('gpt-6-astra', 'medium'), ('gpt-5.6-luna', 'max'), ('gpt-5.6-terra', 'high')],
    'routine': [('gpt-5.6-luna', 'max'), ('gpt-5.6-terra', 'high')],
    'planner': [('gpt-6-astra', 'medium'), ('gpt-5.6-luna', 'max'), ('gpt-5.6-terra', 'high')],
    'coder': [('gpt-5.6-sol', 'high'), ('gpt-5.6-luna', 'max'), ('gpt-5.6-terra', 'high')],
    'specialist': [('gpt-6-astra', 'xhigh'), ('gpt-5.6-luna', 'max'), ('gpt-5.6-terra', 'high')],
}


def digest(data: bytes) -> str: return hashlib.sha256(data).hexdigest()
def read(path: Path) -> bytes: return path.read_bytes() if path.exists() else b""
def atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as out:
        out.write(data); temp = Path(out.name)
    os.replace(temp, path)


def model_catalog() -> set[str] | None:
    """Read only the authenticated local Codex catalog; unavailable is not an error."""
    try:
        result = subprocess.run(['codex', 'debug', 'models'], text=True, encoding='utf-8', errors='replace', capture_output=True, timeout=20, check=True)
        catalog = json.loads(result.stdout or '')
    except (OSError, TypeError, subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return None
    models = catalog.get('models', []) if isinstance(catalog, dict) else catalog
    if not isinstance(models, list): return None
    return {entry.get('slug') or entry.get('model') for entry in models if isinstance(entry, dict) and isinstance(entry.get('slug') or entry.get('model'), str)}


def resolve_mapping(mapping: dict) -> dict:
    """Keep the published preference order, selecting only models this host exposes."""
    available = model_catalog()
    if not available: return copy.deepcopy(mapping)
    resolved = copy.deepcopy(mapping)
    for role, candidates in ROLE_CANDIDATES.items():
        selected = next((candidate for candidate in candidates if candidate[0] in available), None)
        if selected:
            resolved[role]['model'], resolved[role]['reasoning'] = selected
    return resolved

def no_symlink(root: Path, path: Path) -> None:
    """Managed paths are deliberately boring files, never redirected links."""
    try: relative = path.relative_to(root)
    except ValueError: raise SyncError(f"managed path escapes its root: {path}")
    current = root
    if current.is_symlink(): raise SyncError(f"managed root is a symlink: {root}")
    for part in relative.parts:
        current /= part
        if current.exists() and current.is_symlink(): raise SyncError(f"managed path is a symlink: {current}")


def blocks(text: str, names: tuple[str, ...] | None = None) -> dict[str, str]:
    found = {}
    for name in names or tuple(name for item in COMPONENT.values() for name in item["blocks"]):
        start, end = f"<!-- BEGIN:{name} -->", f"<!-- END:{name} -->"
        a, b = text.find(start), text.find(end)
        if ((a < 0) != (b < 0) or b < a or
            (a >= 0 and text.find(start, a + 1) >= 0) or
            (b >= 0 and text.find(end, b + 1) >= 0)):
            raise SyncError(f"unsupported managed block shape in AGENTS.md: {name}")
        if a >= 0: found[name] = text[a:b + len(end)]
    return found


def merge_agents(existing: str, source: str, names: tuple[str, ...]) -> str:
    incoming = blocks(source, names)
    current = blocks(existing, names)
    for name, value in incoming.items():
        if name in current:
            existing = existing.replace(current[name], value)
        else:
            existing = existing.rstrip() + "\n\n" + value + "\n"
    return existing


def in_multiline(lines: list[str], upto: int) -> bool:
    quote = None
    for line in lines[:upto]:
        for marker in ('"""', "'''"):
            if line.count(marker) % 2: quote = marker if quote is None else None
    return quote is not None


def table_at(data: dict, section: str):
    current = data
    for part in section.split("."):
        if not isinstance(current, dict): return None
        current = current.get(part)
    return current


def remove_owned(data: dict, section: str, keys: dict[str, object]) -> None:
    if not section:
        for key in keys: data.pop(key, None)
        return
    parents = []
    current = data
    for part in section.split("."):
        if not isinstance(current, dict) or part not in current: return
        parents.append((current, part)); current = current[part]
    if not isinstance(current, dict): return
    for key in keys: current.pop(key, None)
    for parent, part in reversed(parents):
        if parent.get(part) == {}: parent.pop(part)


def set_toml(text: str, wanted: dict[str, dict[str, object]]) -> str:
    """Edit simple assignments only; reject multiline target values before any write."""
    parsed = tomllib.loads(text) if text.strip() else {}
    if not isinstance(parsed, dict) or ("agents" in parsed and not isinstance(parsed["agents"], dict)):
        raise SyncError("unsupported config.toml shape")
    lines = text.splitlines(keepends=True)
    for section, values in wanted.items():
        actual = parsed if section == "" else table_at(parsed, section)
        if actual and not isinstance(actual, dict): raise SyncError(f"unsupported [{section}] shape")
        positions = {}
        here = ""
        for i, line in enumerate(lines):
            stripped = line.strip()
            if in_multiline(lines, i): continue
            header = re.match(r"^\[([^\[\]]+)\](?:\s*#.*)?$", stripped)
            if header:
                here = header.group(1).strip(); continue
            if here == section:
                for key in values:
                    if stripped.startswith(key) and stripped[len(key):].lstrip().startswith("="):
                        positions[key] = i
        for key, value in values.items():
            if key in positions:
                line = lines[positions[key]]
                if "\"\"\"" in line or "'''" in line: raise SyncError(f"multiline target {section}.{key}")
                comment = ""
                if "#" in line: comment = " " + line[line.index("#"):].rstrip("\r\n")
                ending = "\r\n" if line.endswith("\r\n") else "\n"
                lines[positions[key]] = f"{key} = {json.dumps(value)}{comment}{ending}"
            else:
                if section:
                    headers = [i for i, line in enumerate(lines)
                               if re.match(rf"^\[{re.escape(section)}\](?:\s*#.*)?$", line.strip())]
                    if headers:
                        at = headers[0] + 1
                        while at < len(lines) and not lines[at].strip().startswith("["): at += 1
                        lines.insert(at, f"{key} = {json.dumps(value)}\n")
                    else:
                        if lines and not lines[-1].endswith("\n"): lines[-1] += "\n"
                        lines.extend([f"\n[{section}]\n", f"{key} = {json.dumps(value)}\n"])
                else:
                    at = next((i for i,l in enumerate(lines) if l.strip().startswith("[")), len(lines))
                    lines.insert(at, f"{key} = {json.dumps(value)}\n")
    result = "".join(lines)
    final = tomllib.loads(result)
    before_other, after_other = copy.deepcopy(parsed), copy.deepcopy(final)
    for section, values in wanted.items():
        for data in (before_other, after_other): remove_owned(data, section, values)
    if before_other != after_other: raise SyncError("TOML edit would alter unrelated values")
    for section, values in wanted.items():
        actual = final if section == "" else table_at(final, section)
        if not isinstance(actual, dict) or any(actual.get(k) != v for k, v in values.items()):
            raise SyncError("TOML edit did not produce the requested owned values")
    return result


def owned_values(mapping: dict) -> dict[str, dict[str, object]]:
    coord, routine = mapping["coordinator"], mapping["routine"]
    return {"": {"model": coord["model"], "model_reasoning_effort": coord["reasoning"]}, "models.new_thread": {
        "model": coord["model"], "model_reasoning_effort": coord["reasoning"],
    }, "agents": {
        "enabled": True, "max_concurrent_threads_per_session": 2,
        "default_subagent_model": routine["model"], "default_subagent_reasoning_effort": routine["reasoning"],
    }}


def load_state(path: Path) -> dict: return json.loads(path.read_text()) if path.exists() else {}
def config_values(text: str, wanted: dict) -> dict:
    data = tomllib.loads(text) if text.strip() else {}; got = {}
    for section, keys in wanted.items():
        obj = data if not section else table_at(data, section)
        got[section] = {k: obj.get(k) if isinstance(obj, dict) else None for k in keys}
    return got


def ensure_clean_update(args: argparse.Namespace) -> None:
    if not args.update: return
    env = os.environ | {"GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never"}
    status = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, text=True, capture_output=True, env=env, timeout=30)
    if status.returncode or status.stdout.strip(): raise SyncError("--update requires a clean checkout")
    pull = subprocess.run(["git", "pull", "--ff-only"], cwd=ROOT, env=env, timeout=120)
    if pull.returncode: raise SyncError("git pull --ff-only failed")
    rerun = [sys.executable, str(ROOT / "sync.py")] + [x for x in sys.argv[1:] if x != "--update"]
    raise SystemExit(subprocess.run(rerun).returncode)


def selected_components(args: argparse.Namespace, state: dict) -> tuple[str, ...]:
    available = tuple(name for name in COMPONENTS if (SHARED / name).is_dir())
    explicit = tuple(dict.fromkeys(args.component or ()))
    if "all" in explicit: explicit = available
    if explicit:
        missing = set(explicit) - set(available)
        if missing: raise SyncError("component not available from this checkout: " + ", ".join(sorted(missing)))
        return explicit
    if state:
        if len(available) == 1: return available
        return tuple(name for name in state.get("components", COMPONENTS) if name in available)  # v1 managed both components
    return available


def destination(home: Path, rel: str) -> Path:
    return home / "model-routing" / rel if rel in ("models.json", "REVIEW.md") else home / rel


@contextmanager
def sync_lock(home: Path):
    path = home / "model-routing" / "sync.lock"
    no_symlink(home, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    no_symlink(home, path)
    with path.open("a+b") as handle:
        try:
            if os.name == "nt":
                import msvcrt
                if handle.tell() == 0: handle.write(b"\0"); handle.flush()
                handle.seek(0); msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise SyncError("another sync is running; retry later") from exc
        try: yield
        finally:
            if os.name == "nt": msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else: fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def plan(args: argparse.Namespace) -> tuple[Path, dict[Path, bytes], dict]:
    home = Path(args.codex_home or os.environ.get("CODEX_HOME") or Path.home() / ".codex").expanduser()
    routing = home / "model-routing"; state_path = routing / "sync-state.json"; state = load_state(state_path)
    selected = selected_components(args, state)
    installed = tuple(dict.fromkeys(tuple(state.get("components", COMPONENTS if state else ())) + selected))
    resources_by_component = {name: COMPONENT[name]["resources"] for name in COMPONENTS}
    selected_resources = tuple(rel for name in selected for rel in resources_by_component[name])
    selected_blocks = tuple(block for name in selected for block in COMPONENT[name]["blocks"])
    for name in selected:
        for rel in COMPONENT[name]["resources"] + ("instructions.md",):
            src = SHARED / name / rel
            no_symlink(SHARED, src)
            if not src.is_file(): raise SyncError(f"missing allowlisted source: {name}/{rel}")
    changes: dict[Path, bytes] = {}
    wanted = None
    if "orchestration" in selected:
        mapping = resolve_mapping(json.loads((SHARED / "orchestration" / "models.json").read_text()))
        if not all(k in mapping for k in ("coordinator", "routine", "planner", "coder", "specialist")): raise SyncError("invalid models.json")
        for role in ("coordinator", "routine", "planner", "coder", "specialist"):
            entry = mapping[role]
            if not isinstance(entry, dict) or not all(isinstance(entry.get(k), str) and entry[k] for k in ("model", "reasoning")):
                raise SyncError(f"invalid {role} model mapping")
            if role != "coordinator" and entry.get("agent") != f"quota_{role}": raise SyncError(f"invalid {role} agent mapping")
        wanted = owned_values(mapping)
        config = home / "config.toml"; old_config = read(config).decode("utf-8")
        no_symlink(home, config)
        prior = state.get("config_values")
        current = config_values(old_config, wanted)
        if prior and any(
            current.get(section, {}).get(key) != value
            for section, values in prior.items()
            for key, value in values.items()
        ):
            raise SyncError("local managed config.toml edits detected")
        if not prior and any(v is not None for section in current.values() for v in section.values()) and not args.adopt:
            raise SyncError("existing managed config.toml fields require --adopt")
        new_config = set_toml(old_config, wanted).encode()
        if new_config != read(config): changes[config] = new_config
    agents = home / "AGENTS.md"; old_agents = read(agents).decode("utf-8")
    no_symlink(home, agents)
    override = home / "AGENTS.override.md"
    if override.exists(): raise SyncError("AGENTS.override.md exists; resolve it before syncing")
    old_blocks = blocks(old_agents, selected_blocks)
    prior_blocks = state.get("blocks", {})
    selected_prior_blocks = {k: v for k, v in prior_blocks.items() if k in selected_blocks}
    if selected_prior_blocks and {k: digest(v.encode()) for k, v in old_blocks.items()} != selected_prior_blocks:
        raise SyncError("local managed AGENTS.md edits detected")
    if not selected_prior_blocks and old_blocks and not args.adopt:
        raise SyncError("existing managed AGENTS.md blocks require --adopt")
    instructions = "\n\n".join((SHARED / name / "instructions.md").read_text().replace("<CODEX_HOME>", str(home)) for name in selected)
    new_agents = merge_agents(old_agents, instructions, selected_blocks).encode()
    if new_agents != read(agents): changes[agents] = new_agents
    resources = state.get("resources", {})
    for rel in selected_resources:
        owner = next(name for name in selected if rel in COMPONENT[name]["resources"])
        dest = destination(home, rel)
        src = SHARED / owner / rel
        no_symlink(home, dest)
        old, new = read(dest), read(src)
        if rel == 'models.json':
            new = (json.dumps(mapping, indent=2) + '\n').encode()
        if rel.startswith("agents/quota_"):
            role = rel.removeprefix("agents/quota_").removesuffix(".toml")
            new = set_toml(new.decode(), {"": {"model": mapping[role]["model"], "model_reasoning_effort": mapping[role]["reasoning"]}}).encode()
        old_hash, recorded = digest(old), resources.get(rel)
        if recorded and old_hash != recorded: raise SyncError(f"local managed edit detected: {dest}")
        if not recorded and old and not args.adopt: raise SyncError(f"existing managed file requires --adopt: {dest}")
        if old != new: changes[dest] = new
    state_resources = dict(resources)
    state_resources.update({rel: digest(changes.get(destination(home, rel), read(destination(home, rel)))) for rel in selected_resources})
    state_blocks = dict(prior_blocks)
    state_blocks.update({k: digest(v.encode()) for k, v in blocks(instructions, selected_blocks).items()})
    new_state = {"version": 2, "components": list(installed), "resources": state_resources, "blocks": state_blocks}
    if wanted is not None: new_state["config_values"] = wanted
    elif "config_values" in state: new_state["config_values"] = state["config_values"]
    source_checkouts = dict(state.get("source_checkouts", {}))
    for name in selected: source_checkouts[name] = str(ROOT)
    if source_checkouts: new_state["source_checkouts"] = source_checkouts
    if "orchestration" in selected: new_state["source_checkout"] = str(ROOT)
    elif "source_checkout" in state: new_state["source_checkout"] = state["source_checkout"]
    state_data = json.dumps(new_state, indent=2, sort_keys=True).encode() + b"\n"
    no_symlink(home, state_path)
    if state_data != read(state_path): changes[state_path] = state_data
    return home, changes, state


def apply(args: argparse.Namespace) -> int:
    ensure_clean_update(args)
    if args.check:
        home, changes, _ = plan(args)
        print("would update " + ", ".join(str(p.relative_to(home)) for p in changes))
        return 0
    home = Path(args.codex_home or os.environ.get("CODEX_HOME") or Path.home() / ".codex").expanduser()
    with sync_lock(home):
        return apply_locked(args)


def apply_locked(args: argparse.Namespace) -> int:
    home, changes, _ = plan(args)
    # Re-plan immediately before writes so a concurrent edit becomes a conflict.
    _, checked, _ = plan(args)
    if {p: digest(v) for p,v in changes.items()} != {p: digest(v) for p,v in checked.items()}:
        raise SyncError("files changed during planning; retry")
    backups = home / "model-routing" / "backups" / str(time.time_ns())
    originals = {p: (p.exists(), read(p)) for p in changes}
    written: list[Path] = []
    try:
        for p, (existed, old) in originals.items():
            if old:
                backup = backups / p.relative_to(home)
                no_symlink(home, backup)
                atomic(backup, old)
        for p, data in changes.items():
            atomic(p, data)
            written.append(p)
    except Exception as exc:
        rollback_errors = []
        for p in reversed(written):
            existed, old = originals[p]
            if read(p) != changes[p]: continue  # a concurrent edit wins over rollback
            try:
                if existed: atomic(p, old)
                elif not p.is_symlink(): p.unlink()
            except Exception as rollback: rollback_errors.append(f"{p}: {rollback}")
        if rollback_errors:
            raise SyncError("write failed; rollback incomplete: " + "; ".join(rollback_errors)) from exc
        raise
    print("updated " + ", ".join(str(p.relative_to(home)) for p in changes))
    return 0


def install_schedule(home: Path) -> None:
    scheduler = ROOT / 'schedule.py'
    if not scheduler.is_file(): return
    result = subprocess.run([sys.executable, str(scheduler), '--codex-home', str(home)], check=False)
    if result.returncode:
        raise SyncError('configuration installed, but automatic update scheduling failed')


def run(args: argparse.Namespace) -> int:
    result = apply(args)
    if args.adopt and not args.check and not args.no_schedule:
        home = Path(args.codex_home or os.environ.get("CODEX_HOME") or Path.home() / ".codex").expanduser()
        install_schedule(home)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--codex-home")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--update", action="store_true")
    parser.add_argument("--adopt", action="store_true")
    parser.add_argument("--no-schedule", action="store_true", help="Do not install the automatic updater during initial adoption.")
    parser.add_argument("--component", choices=(*COMPONENTS, "all"), action="append")
    args = parser.parse_args()
    try:
        return run(args)
    except (SyncError, json.JSONDecodeError, tomllib.TOMLDecodeError) as exc:
        print(f"sync failed: {exc}", file=sys.stderr); return 2

if __name__ == "__main__": raise SystemExit(main())
