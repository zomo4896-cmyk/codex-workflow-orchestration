# Codex Workflow Model Orchestration

Workflow-based task decomposition, model allocation, bounded agents, and evidence-based usage review. No ADHD skill is included.

## Paste into Codex to install

```text
Install and enable workflow-aware model orchestration globally on this workstation from https://github.com/zomo4896-cmyk/codex-workflow-orchestration. Follow its AGENTS.md, verify model availability, preserve my existing credentials and machine-specific settings, and enable its automatic Git updates. Install only model orchestration, not ADHD skills. Validate the installation and explain any session-restart requirement.
```

The user runs this prompt in Codex on each workstation. A bare link or GitHub page cannot remotely execute an installation. Windows and Linux are supported; the assistant needs local file/tool access.

For model discovery and personal usage review, use [the Linux/CLI-ready review prompt](REVIEW_PROMPT.md). Automatic Git sync consumes no LLM quota; a model review does. Only designate one recurring review leader.

## Install on Windows or Linux

Requires Python 3.11+, Git, and Codex. This public repository can be cloned without a GitHub account; sign in to Codex separately.

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

Automatic sync checks Git hourly and at login/user-service startup without consuming model quota. Windows task: `CodexSync-orchestration`. Linux timer: `codex-sync-orchestration.timer`. Keep this checkout at its installed path. The Linux user service manager must be active. Public updates are read-only and need no GitHub credentials. A private fork requires its own non-interactive Git authentication.

Restart Codex to load new defaults. Existing sessions may retain their selected model/instructions. Explicit user/project settings and higher-priority instructions can override global defaults.

The installer sets both the normal coordinator default and Codex's managed `[models.new_thread]` default to the mapped coordinator model and reasoning effort. This makes a fresh local Codex thread start on the coordinator route unless it has an explicit model override.

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

Only the designated workstation runs the weekly Codex discovery automation. Maintain shared/orchestration/models.json, validate candidates and policy changes, run tests and sync locally, then commit only explicit generic orchestration source changes to an explicitly authorized repository. Followers only run Git sync. Never publish raw prompts, code, personal usage records, credentials, or backups.

The local compact outcomes log informs the leader's review of verified completion, rework, and escalation. Collection is instruction-driven, not guaranteed telemetry, and the leader does not automatically see other workstation logs. This supports evidence-based adaptation, not a guarantee of continuous optimality or exact quota attribution. Account quota is shared across workstations using the same account.

## Public sharing and personal customization

Only orchestration source files are published here. ADHD skills and the old combined history are not included. Installation is opt-in; this repository grants no access to other workstations. Capability and plan availability vary, and instruction-based routing is not a guarantee of automatic model switching.

Personal outcomes/reviews remain local. For automated changes customized to your own workload across your machines, use your own private fork and explicitly authorize its leader to publish validated mapping/policy changes there. Cloning this public repository grants no upstream publishing permission. Do not publish private telemetry in commits, issues, or pull requests.
