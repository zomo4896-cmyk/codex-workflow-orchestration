# Codex model discovery and personal usage review

Paste the prompt below into an interactive Codex CLI session on the workstation to review. This is one review, not a recurring schedule. It does not depend on desktop-only automation tools.

```text
Perform one Codex model discovery and personal usage review on this workstation using https://github.com/zomo4896-cmyk/codex-workflow-orchestration.

Resolve CODEX_HOME or ~/.codex. Locate the installed orchestration checkout from model-routing/sync-state.json (source_checkouts.orchestration, or source_checkout). If it is not installed, install only the orchestration package first, following the repository's AGENTS.md. Preserve existing credentials, MCP settings, permissions, projects, and unrelated instructions.

Follow the installed model-routing/REVIEW.md. Review the last 30 days of compact local outcomes, capped at 100 records, and the prior local review. Compare verified completion, rework, escalation causes, task decomposition overhead, and model/tool compatibility. Treat missing records as insufficient evidence. Do not upload prompts, source code, paths, usage records, credentials, or personal data.

Check current official OpenAI documentation and models actually available to my Codex account/runtime. Check remaining allowance using a supported mechanism if available. Do not invent quota measurements or use API prices as proof of plan savings. If allowance cannot be verified or is below 10%, skip candidate benchmarks and perform discovery and evidence review only.

Recommend at most one evidence-backed adjustment to the coordinator, routine worker, coder, or difficult-reasoning specialist. For a genuinely promising candidate, run at most three small validation checks in an isolated workspace, including incumbent comparisons within that cap. Never use production mutations, paid APIs, reset credits, or relaxed security settings to run tests. Preserve required verification and explicit user preferences. If evidence is weak, keep the incumbent.

Save a concise local review with sources, verified findings, uncertainty, and the recommended change. Do not push to the public repository or apply an unvalidated model change. If I explicitly authorize applying a validated recommendation, update the authoritative mapping in my chosen checkout, test, back up, and sync its generated local settings. Explain if a local source change will pause upstream sync, and use my own private fork for ongoing personal customization when requested.

Do not create a scheduled review or replace another workstation's discovery leader. Return only meaningful findings, a supported recommendation, or a concrete blocker. Do not claim that saved configuration switches models in sessions already running.
```

For a non-interactive one-off run after installation, review the prompt first and use the installed CLI's supported `codex exec` options. The current CLI accepts stdin via `codex exec -`. A scheduled Linux setup is a separate opt-in action; use only one discovery leader per shared configuration and preserve the workstation's existing permission policy.
