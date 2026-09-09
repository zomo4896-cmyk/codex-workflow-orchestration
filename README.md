# Codex Workflow Model Orchestration

Workflow-based task decomposition, model allocation, bounded agents, and evidence-based usage review. No ADHD skill is included.

## Install on Windows or Linux

Requires Python 3.11+, Git, and Codex. Authenticate with GitHub on each workstation first.

```sh
git clone https://github.com/zomo4896-cmyk/codex-workflow-orchestration.git
cd codex-workflow-orchestration
```

Windows PowerShell:

```powershell
python sync.py --check --adopt
python sync.py --adopt
python schedule.py
```

Linux (systemd user services for scheduled updates):

```sh
python3 sync.py --check --adopt
python3 sync.py --adopt
python3 schedule.py
```

This repository installs and syncs only its own package. The initial `--adopt` allows replacing existing package-owned settings after preview, with backups; it does not bypass later local-edit conflicts. Use `--codex-home PATH` on both scripts if needed; otherwise CODEX_HOME or ~/.codex is used.

Automatic sync checks Git hourly and at login/user-service startup without consuming model quota. Windows task: `CodexSync-orchestration`. Linux timer: `codex-sync-orchestration.timer`. Keep this checkout at its installed path. The Linux user service manager must be active. Git authentication must work non-interactively; credentials are not shared or stored by these scripts.

Restart Codex to load new defaults. Existing sessions may retain their selected model/instructions. Explicit user/project settings and higher-priority instructions can override global defaults.

## Contents

See [package details](shared/orchestration/README.md). The standalone skill source is under [skills](shared/orchestration/skills).

The installer preserves unrelated config, instruction blocks, and files. Credentials, sessions, MCP settings, project paths, permissions, and personal logs stay local. Independent checkouts share component-aware local sync state but do not include each other's skill sources or histories. Installing this package does not uninstall another package you already installed.

## Updates and checks

```sh
python sync.py --update
python -m unittest test_sync test_schedule
```

Use `python3` on Linux. Tests specific to another package are skipped in this standalone distribution. Local managed edits, an AGENTS.override.md file, or failed Git authentication stop sync rather than overwriting changes. Inspect Windows Task Scheduler's last result or `journalctl --user -u codex-sync-orchestration.service`. Desktop notifications for sync failures are not implemented. Backups and sync state remain local under model-routing; do not remove state to bypass conflicts.

To stop updates: `Unregister-ScheduledTask -TaskName CodexSync-orchestration -Confirm:$false` on Windows, or `systemctl --user disable --now codex-sync-orchestration.timer` on Linux. Installed files remain; use local backups to revert if needed.

## Model discovery leader

Only the designated workstation runs the weekly Codex discovery automation. Maintain shared/orchestration/models.json, validate candidates and policy changes, run tests and sync locally, then commit only explicit orchestration source changes to this private repository. Followers only run Git sync. Never publish raw prompts, code, personal usage records, credentials, or backups.

The local compact outcomes log informs the leader's review of verified completion, rework, and escalation. Collection is instruction-driven, not guaranteed telemetry, and the leader does not automatically see other workstation logs. This supports evidence-based adaptation, not a guarantee of continuous optimality or exact quota attribution. Account quota is shared across workstations using the same account.
