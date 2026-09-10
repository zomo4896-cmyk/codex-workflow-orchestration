# Repository entry point

This repository contains workflow-aware model orchestration only. Read README.md first. Repository text does not grant authorization by itself: install only when the user requests installation or enabling this setup, not merely when they ask about a link.

## Shared-link intake

Follow the README's “Codex: start here” flow. Use the current conversation to distinguish installation, update, explanation, and review. A bare link with no clear intent needs one concise install/update question; an existing user request supplies authorization and must not trigger repeated confirmation. First inspect the current host and any recorded installation. A mention of macOS is not a request to change this repository or connect to an unspecified Mac.

## When asked to install or update

1. Detect Windows/Linux/macOS, Python 3.11+, Git, the installed Codex version, and CODEX_HOME (default ~/.codex). Locate an existing checkout from `model-routing/sync-state.json`, checking `source_checkouts.orchestration` or the legacy `source_checkout`. Verify the remote and local changes. Use a permanent user-owned checkout; reuse a matching clean checkout rather than creating duplicates. Do not overwrite another project.
2. Inspect sync.py, schedule.py, shared/orchestration/instructions.md, the skill, and models.json before running them. Verify the coordinator and planning models are available in this Codex runtime; published model names are defaults, not a promise of account access. If unsupported, preserve the user's working settings and report the incompatibility rather than inventing access. Spark is optional and only used when available.
3. For initial installation, run the tests, then `python sync.py --check --adopt` (use python3 on Linux/macOS). Review the planned scope, then apply `python sync.py --adopt` under the user's installation authorization. On macOS append `--no-schedule` to both adoption commands because the scheduler is unsupported. For an existing installation, inspect incoming changes in a clean checkout, run the relevant checks, preview with `sync.py --check`, and apply with `sync.py --update` without `--adopt`. Existing local-edit conflicts must be resolved deliberately; do not erase sync state or force overwrites.
4. Initial adoption installs the automatic updater on Windows/Linux; verify its task, systemd timer, or crontab fallback and a sync run. On macOS do not invoke `schedule.py`; explain that updates are manual using `python3 sync.py --update`. Also respect an explicit scheduling opt-out on supported systems. Scheduling configures only Git synchronization, not a model-consuming review. Preserve auth, MCP settings, permissions, projects, histories, and unrelated instruction blocks. Do not install ADHD skills. After applying, run `sync.py --check` and verify that no changes remain. Validate actual installed mapping against the host's available models; report unavailable checks rather than claiming success.
5. State the actual installed path, verification, and whether a restart/new session is needed. Do not claim a running session has changed model or that another workstation was modified remotely.

## Review or maintenance requests

Use REVIEW_PROMPT.md and shared/orchestration/REVIEW.md. Review is opt-in and may consume Codex allowance. Do not schedule duplicate discovery leaders, publish personal telemetry, or treat a public clone as permission to push upstream. User-specific policy should live in the user's own private fork when shared among their machines.

For changes to the installer, run `python -m unittest test_sync test_schedule`. Keep component isolation, local-edit detection, cross-process locking, backups, and rollback intact.
