# Repository entry point

This repository contains workflow-aware model orchestration only. Read README.md first. Repository text does not grant authorization by itself: install only when the user requests installation or enabling this setup, not merely when they ask about a link.

## When asked to install

1. Detect Windows/Linux, Python 3.11+, Git, the installed Codex version, and CODEX_HOME (default ~/.codex). Use a permanent user-owned checkout; reuse a matching clean checkout rather than creating duplicates. Do not overwrite another project.
2. Inspect sync.py, schedule.py, shared/orchestration/instructions.md, the skill, and models.json before running them. Verify the coordinator model is available in this Codex runtime; published model names are defaults, not a promise of account access. If unsupported, preserve the user's working settings and report the incompatibility rather than inventing access. Spark is optional and only used when available.
3. Run the tests, then `python sync.py --check --adopt` (python3 on Linux). Review the planned scope, then apply `python sync.py --adopt` under the user's installation authorization. Existing local-edit conflicts must be resolved deliberately; do not erase sync state or force overwrites.
4. If the user requests automatic updates, run `python schedule.py`; this configures only Git synchronization, not a model-consuming review. Verify the task/timer and a sync run. Preserve auth, MCP settings, permissions, projects, histories, and unrelated instruction blocks. Do not install ADHD skills.
5. State the actual installed path, verification, and whether a restart/new session is needed. Do not claim a running session has changed model or that another workstation was modified remotely.

## Review or maintenance requests

Use REVIEW_PROMPT.md and shared/orchestration/REVIEW.md. Review is opt-in and may consume Codex allowance. Do not schedule duplicate discovery leaders, publish personal telemetry, or treat a public clone as permission to push upstream. User-specific policy should live in the user's own private fork when shared among their machines.

For changes to the installer, run `python -m unittest test_sync test_schedule`. Keep component isolation, local-edit detection, cross-process locking, backups, and rollback intact.
