#!/usr/bin/env python3
"""Read local Codex rollout records and summarize model usage without modifying them."""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def records(path: Path):
    model = "unknown"
    last_total = 0
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            item = json.loads(line)
            payload = item.get("payload") or {}
            if item.get("type") == "turn_context":
                model = payload.get("model") or model
            usage = payload.get("usage") if item.get("type") == "token_usage_record" else None
            if isinstance(usage, dict):
                total = int(usage.get("total_tokens") or 0)
                delta = max(total - last_total, 0)
                last_total = max(last_total, total)
                yield model, delta, int(usage.get("reasoning_output_tokens") or 0)
    except (OSError, json.JSONDecodeError):
        return


def summarize(sessions: Path, limit: int) -> dict[str, tuple[int, int, int]]:
    totals = defaultdict(lambda: [0, 0, 0])
    paths = sorted(sessions.rglob("rollout-*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
    for path in paths:
        for model, tokens, reasoning in records(path):
            row = totals[model]; row[0] += 1; row[1] += tokens; row[2] += reasoning
    return {model: tuple(values) for model, values in totals.items()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sessions", type=Path, default=Path.home() / ".codex" / "sessions")
    parser.add_argument("--latest", type=int, default=100, help="number of recent rollout files to inspect")
    args = parser.parse_args()
    print("model\tresponses\ttotal_tokens\treasoning_tokens")
    for model, (responses, tokens, reasoning) in sorted(summarize(args.sessions, args.latest).items()):
        print(f"{model}\t{responses}\t{tokens}\t{reasoning}")


if __name__ == "__main__":
    main()
