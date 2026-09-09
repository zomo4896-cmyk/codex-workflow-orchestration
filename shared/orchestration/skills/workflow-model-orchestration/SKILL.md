---
name: workflow-model-orchestration
description: Decompose substantial workflows into bounded tasks, assign suitable available models to agents, integrate results, and optimize verified completion per allowance. Use when workflow-aware model orchestration is requested or enabled globally.
---
# Workflow-aware model orchestration

Resolve `<CODEX_HOME>` below from the CODEX_HOME environment variable, or the current user home directory plus `.codex` when unset.

The user explicitly authorizes automatic task decomposition and model-specific subagent delegation for their requests, without repeated model-selection questions. This does not authorize new external actions, purchases, usage-reset redemption, or separate user-owned tasks. Follow higher-priority tool and runtime constraints.

For every prompt, identify the outcome, uncertainty, required tools, dependencies, and acceptance checks. Handle simple work directly. For substantial work, allocate bounded subtasks while planning; do not force every task through every model or create agents for trivial steps.

Read `<CODEX_HOME>/model-routing/models.json` for current role-to-model and reasoning assignments. This is the canonical mapping; config.toml and agent TOML model fields are synchronized runtime copies. Do not infer model assignments from old conversation messages.

- Coordinator: own scope, integration, communication, and verification. Explicit user model choices prevail. Changing saved defaults does not change the running model.
- Routine role: narrow independent extraction, inventories, and repeatable work.
- Coder role: bounded code implementation or exploration, only when its model and required tools/modalities are available; otherwise use the routine role for narrow work or coordinator for broader work.
- Specialist role: a consequential ambiguous decision or evidenced blocker. Pass the specific question and evidence; do not routinely review successful work with this role.

Use named roles when supported; otherwise explicitly set the available spawn tool's model and compatible reasoning effort. Use a minimal-context fork or no history with a self-contained brief, rather than copying the full conversation. Never silently fall back to an expensive model; report an unavailable route briefly and continue with the coordinator when feasible.

Delegate only when a bounded independent subtask can run alongside useful coordinator work. Prefer one worker, at most two concurrent workers and one specialist worker. Workers do not recursively delegate. Assign disjoint file ownership, relevant sources, constraints, dependencies, and completion checks. Run dependent edits sequentially. Do not duplicate a worker's investigation; integrate its evidence and perform the necessary combined verification.

Escalate based on unresolved uncertainty after targeted investigation, not simply a failed command. Permissions, missing credentials, unavailable services, and rate limits are operational blockers, not reasons to ask a stronger model. Avoid repeated unchanged retries or model cycling. Do not redeem reset credits automatically.

Keep selection seamless: no model-choice questions for routine routing. Mention meaningful delegation or specialist escalation in one short progress update with its purpose; give one consolidated result. Preserve user steering and completed work. When agent tools are unavailable or delegation cannot add value, work directly and do not claim multi-model execution occurred.
## Adapt to observed personal usage

Optimize completed, verified work per allowance, not lowest model price or most agents. At the end of a substantial task, append a compact JSON object to `<CODEX_HOME>/model-routing/outcomes.jsonl` when local file tools are available. Record UTC date, broad task category, observed coordinator/worker model IDs, outcome (verified/partial/blocked), number of genuine rework cycles, escalation reason if any, verification performed, and any observed tool/model incompatibility. Do not include prompts, source code, filenames, credentials, personal content, speculative token counts, or inferred model identities. This log stays local and must never be committed. Skip trivial replies and avoid duplicate entries after interruptions.

Use recent local evidence when choosing comparable tasks: repeated verification failures favor a more capable eligible route; reliable bounded successes favor a cheaper eligible route. Do not generalize a single failure, treat missing access as model weakness, or reduce safety/verification to save quota. The weekly leader review owns permanent shared changes; workers must not rewrite the shared mapping opportunistically.

When current quota is already known to be low, defer optional model benchmarks, speculative reviews, and redundant parallel work. Continue required work using supported routes and disclose a real capacity blocker rather than silently lowering correctness. Do not poll usage on every message. Account-wide usage is shared across machines and is not precise per-task attribution.


## Adapt decomposition to the workflow

Identify the actual workflow and its dependencies before assigning models. These patterns guide decomposition; they are not mandatory agent teams. Small tasks stay with the coordinator. Read model IDs and reasoning settings from the current central mapping instead of embedding them here.

| Workflow | Suitable bounded work | Coordinator responsibility | Specialist trigger |
|---|---|---|---|
| Focused coding | Routine inventory; coder implements a clear change | Trace callers, integrate, run the relevant checks | Consequential ambiguity or an evidenced unresolved defect |
| Frontend or product work | Routine content/component inventory; coder handles settled independent components | Preserve approved design, coordinate shared UI, verify browser flows | Difficult UX or architecture trade-off |
| Operations and debugging | Routine reads of relevant logs/config; coder applies a diagnosed repair | Reproduce, distinguish access/service failures, validate live behavior | Cross-system uncertainty unresolved by targeted investigation |
| Research and documents | Routine extraction from relevant sources; independent source checks where useful | Judge source quality, synthesize, verify claims | Conflicting evidence requiring deeper reasoning |
| Creative or media work | Routine asset inventory; bounded implementation with the appropriate craft tools | Direct and inspect the actual artifact; use domain skills | A specific difficult technical/design decision |

The ADHD skill is optional and controls communication/creative focus only; this skill works without it. Do not impose a creative ideation process on coding, or model routing on an ADHD-only installation. Required specialist skill prerequisites and tool availability still apply.

