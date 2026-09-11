---
name: workflow-model-orchestration
description: Decompose substantial workflows into bounded tasks, assign suitable available models to agents, integrate results, and optimize verified completion per allowance. Use when workflow-aware model orchestration is requested or enabled globally.
---
# Workflow-aware model orchestration

Resolve `<CODEX_HOME>` below from the CODEX_HOME environment variable, or the current user home directory plus `.codex` when unset.

When the user enables this workflow, perform automatic task decomposition and bounded model-specific subagent delegation without repeated model-selection questions. This does not authorize new external actions, purchases, usage-reset redemption, or separate user-owned tasks. Follow higher-priority tool and runtime constraints.

For every prompt, identify the outcome, uncertainty, required tools, dependencies, and acceptance checks. Handle simple work directly. For substantial work, allocate bounded subtasks while planning; do not force every task through every model or create agents for trivial steps.

Read `<CODEX_HOME>/model-routing/models.json` for current role-to-model and reasoning assignments. This is the canonical mapping; config.toml and agent TOML model fields are synchronized runtime copies. Do not infer model assignments from old conversation messages.

## New-model promotion policy

During an authorized model-discovery review, read `<CODEX_HOME>/model-routing/REVIEW.md` and apply its one-tier promotion procedure. A newly introduced, verified Codex model is the trigger to move each eligible role to the next more capable model tier while preserving its exact reasoning level. The current user-defined ladder is Luna → Sol → Astra; extend it only with verified capability evidence. Roles at the highest available tier stay there until a higher eligible tier exists. Use a release record to prevent repeated promotion from the same introduction. This is a discovery-review policy, not a per-prompt catalog check or an automatic action performed by Git sync. Existing model names below describe the starting topology; the current mapping takes precedence after promotion.

- Coordinator: Astra orchestrator owns scope, planning, integration, communication, and verification. Explicit user model choices prevail. Changing saved defaults does not change the running model.
- Routine role: Luna explorer or researcher for bounded investigation, inventories, evidence, and focused lookup.
- Planner role: lead consequential discovery, option comparison, workload allocation, and the executable plan; use the strongest eligible planning route only when the decision warrants it.
- Coder role: bounded code implementation or exploration, only when its model and required tools/modalities are available; otherwise use the routine role for narrow work or coordinator for broader work.
- Specialist role: Astra xhigh independent review only for a material risk after implementation and focused tests.

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
| Deep dive, brainstorming, or a new approach | Routine evidence and precedent scan; up to three distinct approaches | Frame the decision, compare options, recommend a direction, and turn the chosen direction into a plan | Consequential ambiguity after evidence is gathered |

The ADHD skill is optional and controls communication/creative focus only; this skill works without it. Do not impose a creative ideation process on coding, or model routing on an ADHD-only installation. Required specialist skill prerequisites and tool availability still apply.

## Staged delegation

For substantial repository work, use stages rather than a generic pool of agents:

| Stage | Role | Default route | Owns |
|---|---|---|---|
| Frame | coordinator | coordinator | The decision question, constraints, success criteria, and what is out of scope. |
| Map | explorer | routine / Luna max | Relevant files, execution path, constraints, and existing tests. Read-only. |
| Explore | researcher | routine / Luna max | Evidence, precedents, and up to three materially different feasible approaches. Read-only. |
| Evaluate | planning lead | planner / Astra | Trade-offs, assumptions, workload allocation, and a recommended direction. Read-only. |
| Decide | architect | specialist / Astra | Compare short-listed architecture choices before a consequential implementation begins. Read-only. |
| Plan | planning lead | planner / Astra | Ordered work, dependencies, ownership, suitable role assignments, and acceptance checks. Read-only. |
| Build and test | worker | coder / Sol high | One bounded implementation surface and its focused tests. |
| Verify facts | researcher | routine / Luna max | Version-specific or external facts from primary sources. Read-only. |
| Review | reviewer | specialist / Astra xhigh | Independent material correctness, security, integrity, concurrency, or compatibility review. Read-only. |

Use the actual available agent type that matches the route. Role names describe the contract; they do not require an agent if the task is too small to benefit from one.

Delegate when a task spans multiple modules, needs repository mapping, has independent workstreams, crosses a runtime boundary, or needs verified external facts. Keep a localized and well-understood change with the coordinator. Do not delegate merely to satisfy a process rule.

### Draw a small task graph

Before delegating substantial work, list the bounded nodes, required evidence, and dependency edges. Fan out only nodes with no dependency between them, such as independent repository maps or external fact checks. Gate planning, implementation, integration, and review on the results they need. Keep the graph small: the existing two-worker cap remains the limit.

Each completed node returns a concise evidence summary that becomes the next node's input. The coordinator freezes accepted facts, resolves conflicts, and decides whether a failed verification needs a narrow retry, a revised plan, or no further work. Do not force exploratory work into a graph before the question is clear; do not parallelize a real dependency chain.

### Discovery before planning

When the user asks to **deeper dive**, **brainstorm**, **explore new ideas**, **find a new way**, **rethink**, or **compare approaches**, do not jump to implementation. Use: **frame → map/evidence → explore alternatives → evaluate → Astra design gate when warranted → coordinator recommendation → plan**.

Frame the decision in one sentence, identify constraints and success criteria, then generate no more than three meaningfully distinct approaches. Compare each against evidence, risks, reversibility, effort, and fit with existing work. Return a recommended direction, the viable alternatives and why they were not selected, remaining unknowns, and the next reversible action. Do not start a worker or mutate project files until the user chooses a direction or has explicitly asked to proceed with the recommendation.

Use the planner for consequential discovery and planning after alternatives and evidence are short-listed. It assigns workload by task shape: routine for bounded evidence or proof, coder for settled isolated implementation, coordinator for integration and dependent work, and specialist only for a material unresolved decision. For a small or well-understood task, the coordinator plans directly. Astra is a decision synthesizer and planning lead when eligible, not the default brainstormer; routine evidence scans keep ordinary ideation fast and quota-aware.

For delegated implementation after a direction is chosen, use: **Astra plan → Luna map/research in parallel when useful → Sol build and focused tests → Astra integrate and verify → Astra xhigh review only when needed**. Do not spawn every role; run only bounded work that improves the result. Serialize dependent edits. The coordinator owns architecture, integration, and the final result.

Run the Astra design gate before implementation when choices differ materially in module boundaries, data ownership, public APIs, permissions, schema or migration risk, concurrency, operational recovery, or long-term maintenance. Give Astra the mapped evidence and 2–3 feasible options, not an unbounded request to redesign the system. Require a concise decision record: recommendation, rejected alternatives, trade-offs, non-goals, and acceptance criteria. The coordinator accepts, narrows, or rejects that recommendation.

Do not invoke Astra for an architecture gate when existing patterns and a localized change already determine the implementation. The gate is for making one costly decision well; it is not a mandatory planning ceremony.

Use the reviewer only when a defect would be costly or difficult to detect through focused tests: security, data integrity, concurrency, permission changes, public API compatibility, or an unresolved design trade-off. Do not run an Astra review automatically for routine successful changes.

Give every agent one bounded contract: objective, scope, constraints, deliverable, and acceptance check. Explorers, researchers, testers, and reviewers return evidence instead of changing production files. Workers stop and return control when a task requires a wider architecture, schema, dependency, or security decision.

## Measure routed work

For meaningful delegated work, prefer Codex's local rollout records when available to compare thread models, response counts, cached input, and reasoning output. Use those records with the compact outcomes log before changing assignments. Treat one short run, account-wide quota changes, and anecdotal screenshots as insufficient evidence for a permanent routing change.
