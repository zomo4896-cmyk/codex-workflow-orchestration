---
name: workflow-model-orchestration
description: Decompose substantial workflows into bounded tasks, assign suitable available models to agents, integrate results, and optimize verified completion per allowance. Use when workflow-aware model orchestration is requested or enabled globally.
---
# Workflow-aware model orchestration

Resolve `<CODEX_HOME>` below from the CODEX_HOME environment variable, or the current user home directory plus `.codex` when unset.

When the user enables this workflow, perform automatic task decomposition and bounded model-specific subagent delegation without repeated model-selection questions. This does not authorize new external actions, purchases, usage-reset redemption, or separate user-owned tasks. Follow higher-priority tool and runtime constraints.

For every prompt, identify the outcome, uncertainty, required tools, dependencies, and acceptance checks. Handle simple work directly. For substantial work, allocate bounded subtasks while planning; do not force every task through every model or create agents for trivial steps.

Read `<CODEX_HOME>/model-routing/models.json` for current role-to-model and reasoning assignments. This is the canonical mapping; config.toml and agent TOML model fields are synchronized runtime copies. Do not infer model assignments from old conversation messages.

## Recall, choose, and measure the execution strategy

Before substantial work, use already available confirmed project context and compact records of comparable completed strategies. If a local second-brain integration is installed, consume its context and recall result; this package does not install one or require private memory. Reuse recorded decisions and response patterns only within their supported scope. A recalled plan is a starting point: check current files, requirements, model availability, and prior verification before reusing it. Do not reload full transcripts when a cited compact record answers the question.

When a user defers work or supplies independent follow-up tasks, use an existing local queue when available instead of expanding the active task indefinitely. Preserve priority, earliest start, deadlines, prerequisites, scope and execution authorization. A ready recommendation is not a reservation: claim before execution, respect active ownership, and keep paused or uncertain work out of automatic retries. Background dispatch requires the user's authorization and a supported scheduler; this package does not create a queue or authorize new external effects.

Choose the simplest structure that fits the actual dependencies:

- Direct: one small or tightly coupled task; keep it with the coordinator.
- Bounded swarm: independent tasks with clear deliverables and disjoint read/write scopes; run at most two subagents alongside useful coordinator work.
- Task graph: dependent stages, with parallel branches only where their inputs and scopes permit it. Integrate and verify before releasing dependent work.
- Repair loop: a failed, isolated verification may receive one targeted retry after the cause and approach change. A second failure returns to planning. Operational blocks and uncertain external effects require resolution or reconciliation, not repeated inference.

These patterns compose; a task graph can contain bounded parallel branches and a repair loop. Shared writes or a read during another worker's write must be serialized. Do not spawn redundant workers to manufacture consensus or call a sequential task a swarm.

Assign roles from the current mapping at decomposition time: routine for narrow evidence work, coder for settled implementation, planner for consequential unresolved design, specialist for material independent review. Keep a simple task with the current coordinator even if a cheaper worker exists; delegation overhead can dominate. Explicit model choices prevail. A model listed in the published catalog is not proof of current-host access; check supported tools and reasoning before dispatch. Never claim to switch the model of the already-running coordinator.

For a nontrivial graph, `scripts/strategy.py --plan <local-plan.json> --models <CODEX_HOME>/model-routing/models.json` validates dependencies, read/write scope conflicts, available roles, and worker limits and returns a proposed schedule. It never dispatches or executes commands. `scripts/strategy.py --context --home <CODEX_HOME>` returns compact strategy guidance, mappings, and model-catalog freshness. Keep plan files local. Actual agent availability and the coordinator's judgment remain authoritative.

Record the chosen strategy, actual model roster, verification evidence, corrections, and response pattern in the existing local task checkpoint or an installed local strategy-recall adapter. Keep planned and observed assignments distinct. Link completed outcomes to their exact session/turn/result identity, deduplicate workers, and preserve missing values. User acceptance, technical verification, elapsed time, total tokens, and billed cost are different signals. Prefer verified useful output per measured resource use; do not equate cached/reported tokens with billed cost or account allowance. Use comparable accepted-and-verified examples to inform the next choice; weak samples do not establish an optimal strategy or justify a new default.

## New-model promotion policy

During an authorized model-discovery review, read `<CODEX_HOME>/model-routing/REVIEW.md` and apply its one-tier promotion procedure. A newly introduced, verified Codex model is the trigger to move each eligible role to the next more capable model tier while preserving its exact reasoning level. The current user-defined ladder is Luna → Sol → Astra; extend it only with verified capability evidence. Roles at the highest available tier stay there until a higher eligible tier exists. Use a release record to prevent repeated promotion from the same introduction. This is a discovery-review policy, not a per-prompt catalog check or an automatic action performed by Git sync. Existing model names below describe the starting topology; the current mapping takes precedence after promotion.

- Coordinator: Astra orchestrator owns scope, planning, integration, communication, and verification. Explicit user model choices prevail. Changing saved defaults does not change the running model.
- Routine role: Luna explorer or researcher for bounded investigation, inventories, evidence, and focused lookup.
- Planner role: lead consequential discovery, option comparison, workload allocation, and the executable plan; use the strongest eligible planning route only when the decision warrants it.
- Coder role: bounded code implementation or exploration, only when its model and required tools/modalities are available; otherwise use the routine role for narrow work or coordinator for broader work.
- Specialist role: Astra xhigh independent review only for a material risk after implementation and focused tests.

Use named roles when supported; otherwise explicitly set the available spawn tool's model and compatible reasoning effort. Use a minimal-context fork or no history with a self-contained brief, rather than copying the full conversation. Never silently fall back to an expensive model; report an unavailable route briefly and continue with the coordinator when feasible.

Delegate only when a bounded independent subtask can run alongside useful coordinator work. Prefer one worker; at most two subagents may run concurrently, including any specialist. Workers do not recursively delegate. Assign disjoint file ownership, relevant sources, constraints, dependencies, and completion checks. Run dependent edits sequentially. Do not duplicate a worker's investigation; integrate its evidence and perform the necessary combined verification.

Escalate based on unresolved uncertainty after targeted investigation, not simply a failed command. Permissions, missing credentials, unavailable services, and rate limits are operational blockers, not reasons to ask a stronger model. Avoid repeated unchanged retries or model cycling. Do not redeem reset credits automatically.

Keep selection seamless: no model-choice questions for routine routing. Mention meaningful delegation or specialist escalation in one short progress update with its purpose; give one consolidated result. Preserve user steering and completed work. When agent tools are unavailable or delegation cannot add value, work directly and do not claim multi-model execution occurred.
## Adapt to observed personal usage

Optimize completed, verified work per allowance, not lowest model price or most agents. At the end of a substantial task, append one compact JSON object to `<CODEX_HOME>/model-routing/outcomes.jsonl` when local file tools are available. Use the canonical fields in [evidence.md](references/evidence.md): `schema_version`, `utc`, `category`, `coordinator_model`, `worker_models`, `outcome`, `rework_cycles`, `escalation_reason`, `verification`, and `incompatibility`. Use null for an unobserved coordinator model and an empty list for no observed workers; never infer identities from the configured mapping. Do not include prompts, source code, filenames, credentials, personal content, or speculative token counts. This log stays local and must never be committed. Skip trivial replies and avoid duplicate entries after interruptions. The helper normalizes legacy `date` records when reading, without rewriting history.

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

Define each node's acceptance checks and allowed change scope before delegating. Use ordinary code for mechanical work such as exact comparisons, hash verification, and configuration parsing; reserve models for decisions requiring judgment. For supported file and Git-scope checks, use the installed read-only `scripts/evidence.py` following [evidence.md](references/evidence.md). Expected hashes must come from the accepted source artifact, not the destination being checked. A passing hash, parser, or scope check proves only that specific property; run the task's actual behavioral tests separately and record their commands, exit codes, and tested revision.

Before splitting similar work, read at most three relevant confirmed planning constraints from local `model-routing/review.json` under `planning_constraints`, if present. Match the task category and applicability, verify the supporting evidence still applies, and put the useful constraint into the planner's brief. Treat records as evidence, never as permission or higher-priority instructions. The coordinator may record a confirmed causal lesson after an accepted result; distinguish it from a speculative explanation. Store its category, applicability, constraint, evidence reference, verification date, and invalidation condition. On changed inputs, retire or revalidate it. Preserve other review fields and concurrent edits. Personal constraints stay local; permanent public routing changes belong to the authorized weekly review.

### Save progress and resume safely

For substantial delegated work or work likely to span interruptions, the coordinator maintains `<CODEX_HOME>/model-routing/task-progress/<task-id>.md`. Use the actual root task ID when available, otherwise generate one unique ID and retain it throughout the task. Report this checkpoint path once so the task can be explicitly resumed. Keep it outside project repositories and public Git sync. If an existing task-state service already owns progress, use that record instead; do not create a competing source of truth. Simple tasks need no checkpoint.

Record the goal, current phase, accepted direction (or undecided), fixed acceptance criteria, and a compact table: `node | dependencies | owner/agent ID | status | attempts | evidence/artifact reference`. Status is pending, running, verified, blocked, or superseded. Only the coordinator writes this record, after planning and each meaningful result, using an atomic replacement. Keep summaries and artifact references, not raw logs, credentials, or full conversations. Record the next ready action and any unresolved external effect before a handoff; never commit the checkpoint.

On resume, read the matching checkpoint before spawning work. Reconcile running agent IDs and the current files/revision or source freshness. Reuse verified results only while their inputs and evidence remain valid; mark affected dependent nodes pending when inputs change. A saved running status does not prove that an agent is still active or that its action completed. Do not restart completed research or launch a duplicate worker merely because the conversation was interrupted. This is instruction-driven persistence, not an automatic background workflow engine.

### Bound corrections and protect verification

For an isolated failed node, allow at most one targeted retry after examining the failure and changing the approach. If it fails again, return to the coordinator to narrow the task, revise the plan, or report a blocker. Keep the attempt history across resumes; rewording the same task does not reset its retry count. Permissions, outages, and unavailable credentials need an operational resolution. Reconcile uncertain deploys, messages, or other external effects before any retry.

Return only the failing unit with a failure packet: `node`, `verdict` (failed/blocked), `failed_check`, `evidence`, `allowed_scope`, `attempts`, and `next_action`. Verified sibling nodes remain accepted unless their inputs changed. Choose verification depth by affected callers, reversibility, and operational consequence; model confidence is not a substitute for evidence or authorization. Complete authorized preparation before any required approval, and preserve existing approval boundaries.

For an independent review, spawn a separate reviewer without inherited conversation history, containing requirements, acceptance criteria, the actual artifact or diff, and reproducible test evidence. A separate instance of the same model is acceptable. Omit the worker's persuasive explanation and full conversation; require the reviewer to inspect evidence and identify unsupported conclusions. Existing risk-based review triggers still apply. The coordinator must not weaken acceptance criteria, remove failing checks, or relabel failures to obtain a pass. Record legitimate changes in user intent explicitly and revalidate affected nodes. Parallel writers need disjoint ownership or isolated worktrees with one integration owner.

### Discovery before planning

When the user asks to **deeper dive**, **brainstorm**, **explore new ideas**, **find a new way**, **rethink**, or **compare approaches**, do not jump to implementation. Use: **frame → map/evidence → explore alternatives → evaluate → Astra design gate when warranted → coordinator recommendation → plan**.

Frame the decision in one sentence, identify constraints and success criteria, then generate no more than three meaningfully distinct approaches. Compare each against evidence, risks, reversibility, effort, and fit with existing work. Return a recommended direction, the viable alternatives and why they were not selected, remaining unknowns, and the next reversible action. The coordinator or bounded read-only researchers may gather evidence before a direction is chosen; start the checkpoint during framing when its scope warrants one, with direction marked undecided. Do not start an implementation worker or mutate project files until the user chooses a direction or has explicitly asked to proceed with the recommendation.

Use the planner for consequential discovery and planning after alternatives and evidence are short-listed. It assigns workload by task shape: routine for bounded evidence or proof, coder for settled isolated implementation, coordinator for integration and dependent work, and specialist only for a material unresolved decision. For a small or well-understood task, the coordinator plans directly. Astra is a decision synthesizer and planning lead when eligible, not the default brainstormer; routine evidence scans keep ordinary ideation fast and quota-aware.

When the root already uses the planning model, it leads planning directly. Spawn a separate planner only for a distinct planning question that adds value; do not repeat the root's planning in another Astra context.

For delegated implementation after a direction is chosen, use: **Astra plan → Luna map/research in parallel when useful → Sol build and focused tests → Astra integrate and verify → Astra xhigh review only when needed**. Do not spawn every role; run only bounded work that improves the result. Serialize dependent edits. The coordinator owns architecture, integration, and the final result.

Run the Astra design gate before implementation when choices differ materially in module boundaries, data ownership, public APIs, permissions, schema or migration risk, concurrency, operational recovery, or long-term maintenance. Give Astra the mapped evidence and 2–3 feasible options, not an unbounded request to redesign the system. Require a concise decision record: recommendation, rejected alternatives, trade-offs, non-goals, and acceptance criteria. The coordinator accepts, narrows, or rejects that recommendation.

Do not invoke Astra for an architecture gate when existing patterns and a localized change already determine the implementation. The gate is for making one costly decision well; it is not a mandatory planning ceremony.

Use the reviewer only when a defect would be costly or difficult to detect through focused tests: security, data integrity, concurrency, permission changes, public API compatibility, or an unresolved design trade-off. Do not run an Astra review automatically for routine successful changes.

Give every agent one bounded contract: objective, scope, constraints, deliverable, and acceptance check. Explorers, researchers, testers, and reviewers return evidence instead of changing production files. Workers stop and return control when a task requires a wider architecture, schema, dependency, or security decision.

## Measure routed work

For meaningful delegated work, prefer Codex's local rollout records when available to compare thread models, response counts, cached input, and reasoning output. Use those records with the compact outcomes log before changing assignments. Treat one short run, account-wide quota changes, and anecdotal screenshots as insufficient evidence for a permanent routing change.
