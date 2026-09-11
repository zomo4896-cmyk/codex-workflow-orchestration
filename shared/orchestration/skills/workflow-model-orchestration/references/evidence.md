# Mechanical evidence and local learning

Read this when defining mechanical gates, recording outcomes, or retrieving planning constraints. The helper uses Python 3.11+ and is read-only. It neither runs tests nor grants approval to deploy.

## Verify an accepted artifact

Run `python <skill-directory>/scripts/evidence.py verify --manifest <local-manifest.json>` (use python3 on Linux). Keep manifests local and outside public commits.

Manifest shape:

```json
{
  "root": "/absolute/path/to/target",
  "files": [
    {"path": "models.json", "sha256": "<64 hex characters from accepted source>", "format": "json"},
    {"path": "agents/quota_coder.toml", "sha256": "<64 hex characters from accepted source>", "format": "toml"}
  ]
}
```

Use the actual absolute Windows or Linux root. Paths are relative to that root; escaping paths are rejected. Format is optional; supported formats are json and toml. File checks require an expected SHA256. Compare rendered source expectations when an installer intentionally transforms a file. Do not derive the expected hash from the destination being verified.

For a Git working tree, add `"git_scope": {"base": "<recorded base commit>", "allowed": ["src/feature.py", "tests/test_feature.py"]}`. Root must be the repository root. Allowed paths are exact names, not globs. Scope checks include changes from the base to the working tree, staged/unstaged edits, and untracked nonignored files. Renames require both old and new paths. Record pre-existing user changes during planning; do not discard them or attribute them to the worker. Use an isolated worktree if scope cannot be evaluated cleanly.

A failed check exits nonzero with structured diagnostics. Passing checks mean hashes/syntax/scope matched, not that behavior is correct. Run behavioral tests separately; retain the tested revision, command, and actual exit code. Configuration semantics still need the appropriate application's own check. A valid JSON file is not proof of a valid application configuration.

## Outcomes

New local outcomes use this schema:

```json
{
  "schema_version": 1,
  "utc": "2026-09-11T00:00:00Z",
  "category": "orchestration_maintenance",
  "coordinator_model": null,
  "worker_models": [],
  "outcome": "verified",
  "rework_cycles": 0,
  "escalation_reason": null,
  "verification": "Relevant checks completed; recorded results reviewed",
  "incompatibility": null
}
```

Use a timezone-aware UTC timestamp, broad category, observed model IDs only, and verified/partial/blocked outcome. Rework is a nonnegative integer, not a token estimate. Model IDs may be unknown. Text fields describe generic checks or blockers, without prompts, paths, credentials, source code, or personal content.

Read history with `python <skill-directory>/scripts/evidence.py outcomes --path <CODEX_HOME>/model-routing/outcomes.jsonl --limit 100`. This normalizes legacy date/utc records in its output and reports invalid lines without printing raw records. It does not migrate or overwrite the original log. Do not infer savings from tiny samples or translate token totals into exact account quota.

## Failure packet and planning constraint

A correction packet carries `node`, `verdict`, `failed_check`, `evidence`, `allowed_scope`, `attempts`, and `next_action`. Link the actual failing result in the local checkpoint; send only the affected unit back. Existing retry limits apply across resumptions.

Use the existing private `model-routing/review.json` field `planning_constraints` for confirmed lessons. Each entry has `category`, `applicability`, `constraint`, `evidence`, `verified_utc`, and `invalidation`. Reference evidence rather than copying logs. An explicit error followed by a validated repair can support a narrowly scoped lesson; broader rules need repeated evidence. Before planning, read at most three relevant entries and recheck applicability. Do not load every historic lesson into every agent.

Example: a validated installation under the correct account can establish an ownership constraint for later multi-account updates. It does not authorize elevated access or justify changing another account's permissions. Keep personal constraints and their evidence local. Generic policy changes still go through the authorized review, tests, and publication process. This retrieval is instruction-driven, not an autonomous learning service.
