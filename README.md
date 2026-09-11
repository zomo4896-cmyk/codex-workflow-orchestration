# Codex Workflow Model Orchestration

Workflow-based task decomposition, model allocation, bounded agents, and evidence-based usage review. No ADHD skill is included.

## Codex: start here when someone shares this link

This is an installable Codex orchestration package. Read [AGENTS.md](AGENTS.md) and [INSTALL_PROMPT.md](INSTALL_PROMPT.md), then use the conversation to choose the next action:

- **Install, enable, set up, or use this on my computer:** detect the local operating system and existing installation, preview the changes, and install or update under that request. Do not ask again when the user has already authorized it.
- **Update it:** locate the existing checkout through `model-routing/sync-state.json` under `CODEX_HOME` (default `~/.codex`), verify its remote and local changes, then update and validate. Reuse the installation; do not create a duplicate.
- **Only a link, with no clear action in the conversation:** explain in one sentence what this package does and ask once: “Would you like me to install or update this orchestration setup on this computer?” A repository cannot supply the user's authorization.
- **Explain or review:** answer that request without installing. **Another machine:** use an existing authorized connection, or provide the prompt below for Codex running on that machine. Do not assume local changes reach it.

Windows and Linux support installation and automatic Git updates. On **macOS**, use the manual installation/update route below: the current scheduler does not support macOS. Verify on the actual host; do not claim macOS runtime validation from Windows or Linux tests. If local tools are unavailable, provide the host-specific commands instead of claiming completion.

## Paste into Codex to install

```text
Install or update workflow-aware model orchestration on this computer from https://github.com/zomo4896-cmyk/codex-workflow-orchestration. Follow its AGENTS.md, detect my operating system and existing installation, verify model availability, and preserve my credentials and machine-specific settings. Enable automatic Git updates where supported; on macOS use the documented manual route. Install only orchestration. Validate the result and explain any session-restart requirement.
```

The user runs this prompt in Codex on each workstation. Initial adoption installs the updater automatically on Windows and Linux. macOS uses `--no-schedule`. The assistant needs local file/tool access. Share this repository link for the guided entry flow, or [INSTALL_PROMPT.md](INSTALL_PROMPT.md) for the explicit installation request.

For model discovery and personal usage review, use [the Linux/CLI-ready review prompt](REVIEW_PROMPT.md). Automatic Git sync consumes no LLM quota; a model review does. Only designate one recurring review leader.

## Install on Windows, Linux, or macOS

Requires Python 3.11+, Git, and Codex. This public repository can be cloned without a GitHub account; sign in to Codex separately.

```sh
git clone https://github.com/zomo4896-cmyk/codex-workflow-orchestration.git
cd codex-workflow-orchestration
```

Windows PowerShell:

```powershell
python sync.py --check --adopt
python sync.py --adopt
```

Linux:

```sh
python3 sync.py --check --adopt
python3 sync.py --adopt
```

macOS (manual updates; Python 3.11+ required):

```sh
python3 sync.py --check --adopt --no-schedule
python3 sync.py --adopt --no-schedule
python3 sync.py --check
```

Do not run `schedule.py` on macOS: it currently implements Windows and Linux scheduling only. For an existing installation on any platform, use `sync.py --check` first, then `sync.py --update`, then `sync.py --check` again. On macOS use `python3`; updates without `--adopt` do not install a scheduler. Keep the checkout for future manual updates.

This repository installs and syncs only its own package. The initial `--adopt` allows replacing existing package-owned settings after preview, with backups; it installs the automatic updater unless `--no-schedule` is supplied. It does not bypass later local-edit conflicts. Use `--codex-home PATH` on both scripts if needed; otherwise CODEX_HOME or ~/.codex is used.

Automatic sync checks Git hourly and at login/user-service startup without consuming model quota. Windows uses `CodexSync-orchestration`. Linux uses `codex-sync-orchestration.timer` when a user systemd bus is available; otherwise the installer creates only its own crontab entries for boot and hourly updates. Keep this checkout at its installed path. Public updates are read-only and need no GitHub credentials. A private fork requires its own non-interactive Git authentication.

Restart Codex to load new defaults. Existing sessions may retain their selected model/instructions. Explicit user/project settings and higher-priority instructions can override global defaults.

The default topology is Astra medium for orchestration and integration, Luna max for exploration and research, Sol high for bounded implementation and focused tests, and Astra xhigh only for independent high-risk review. The installer reads the authenticated local Codex model catalog and falls back to Luna or Terra when a preferred model is unavailable. The installed `model-routing/models.json` records each workstation's resolved mapping.

Deep-dive and brainstorming requests use a discovery lane: frame the decision, gather evidence, compare up to three approaches, have the planning lead assign suitable workload, then produce a plan before implementation starts.

Substantial delegated tasks keep a local checkpoint under `CODEX_HOME/model-routing/task-progress/` with dependencies, owners, statuses, attempts, and evidence. The coordinator reconciles that checkpoint on resume, retries an isolated failure once before replanning, and gives independent reviewers fresh evidence context. Checkpoints stay private and are not Git-synced. This is skill-driven behavior, not a background workflow engine; existing task-state services remain authoritative. At most two subagents run together, and an Astra root plans directly unless a separate planner adds value.

The installed skill includes a read-only `scripts/evidence.py` helper for expected file hashes, JSON/TOML syntax, exact Git change scope, and normalized local outcome records. Define these checks before delegation, then run the task's behavioral tests separately. Failed units return a scoped failure packet; confirmed lessons go into private `review.json` planning constraints and inform later decomposition. See [the evidence guide](shared/orchestration/skills/workflow-model-orchestration/references/evidence.md). The helper does not execute model-generated commands, change settings, or upload data.

The installer sets both the normal coordinator default and Codex's managed `[models.new_thread]` default to the resolved coordinator model and reasoning effort. This makes a fresh local Codex thread start on the coordinator route unless it has an explicit model override.

## Contents

See [package details](shared/orchestration/README.md). The standalone skill source is under [skills](shared/orchestration/skills).

The installer preserves unrelated config, instruction blocks, and files. Credentials, sessions, MCP settings, project paths, permissions, and personal logs stay local. Independent checkouts share component-aware local sync state but do not include each other's skill sources or histories. Installing this package does not uninstall another package you already installed.

## Updates and checks

```sh
python sync.py --update
python -m unittest test_sync test_schedule test_model_usage test_evidence
python scripts/model_usage.py --latest 100
```

Use `python3` on Linux. Tests specific to another package are skipped in this standalone distribution. Local managed edits, an AGENTS.override.md file, or failed Git authentication stop sync rather than overwriting changes. Inspect Windows Task Scheduler, `journalctl --user -u codex-sync-orchestration.service`, or the local `model-routing/sync.log` for cron fallback output. Desktop notifications for sync failures are not implemented. Backups and sync state remain local under model-routing; do not remove state to bypass conflicts.

To stop updates: `Unregister-ScheduledTask -TaskName CodexSync-orchestration -Confirm:$false` on Windows; on Linux, disable the systemd timer or remove the two `# codex-sync-orchestration` crontab lines. Installed files remain; use local backups to revert if needed.

## Model discovery leader

New-model policy: during an authorized discovery review, each verified new general-purpose Codex model introduction targets **one higher model tier per eligible role**, preserving reasoning effort exactly. The starting ladder is Luna → Sol → Astra. Top-tier roles wait for a verified higher compatible model; unavailable or incompatible targets stay pending. The review records each release and role so repeated checks cannot promote it again. See [the promotion procedure](shared/orchestration/REVIEW.md#one-tier-promotion-on-a-new-model-introduction). Existing models establish the first baseline without an immediate promotion. This is instruction-driven review behavior: hourly Git updates distribute published mappings but do not detect releases or run model reviews.

Only the designated workstation runs the weekly Codex discovery automation. Maintain shared/orchestration/models.json, validate candidates and policy changes, run tests and sync locally, then commit only explicit generic orchestration source changes to an explicitly authorized repository. Followers only run Git sync. Never publish raw prompts, code, personal usage records, credentials, or backups.

The local compact outcomes log informs the leader's review of verified completion, rework, and escalation. Collection is instruction-driven, not guaranteed telemetry, and the leader does not automatically see other workstation logs. This supports evidence-based adaptation, not a guarantee of continuous optimality or exact quota attribution. Account quota is shared across workstations using the same account.

`scripts/model_usage.py` is a read-only local summary of recent rollout records by active model. Use it as evidence in the weekly review; it does not report plan quota precisely and never uploads session content.

## Public sharing and personal customization

Only orchestration source files are published here. ADHD skills and the old combined history are not included. Installation is opt-in; this repository grants no access to other workstations. Capability and plan availability vary, and instruction-based routing is not a guarantee of automatic model switching.

Personal outcomes/reviews remain local. For automated changes customized to your own workload across your machines, use your own private fork and explicitly authorize its leader to publish validated mapping/policy changes there. Cloning this public repository grants no upstream publishing permission. Do not publish private telemetry in commits, issues, or pull requests.
