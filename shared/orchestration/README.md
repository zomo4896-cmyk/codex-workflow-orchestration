# Workflow model orchestration

Independent task-decomposition and model-allocation package. It does not install ADHD communication or creative workflows.

- [Orchestration skill](skills/workflow-model-orchestration/SKILL.md): selects bounded work based on the workflow, dependencies, uncertainty, required tools, and acceptance checks.
- [Model mapping](models.json): the maintained model/effort assignments; generated runtime copies are synchronized by the installer.
- [Agents](agents): routine, coding, and difficult-reasoning roles.
- [Review procedure](REVIEW.md): bounded discovery and evidence-based personal-usage optimization on one designated leader.

Workflow patterns cover coding, frontend/product, operations/debugging, research/documents, and creative/media work. These guide allocation; they do not force a team for every prompt. Small tasks stay with the coordinator.

From the repository root (use `python3` on Linux):

```sh
python sync.py --component orchestration --check --adopt
python sync.py --component orchestration --adopt
python schedule.py
```

This installs only the orchestration global block/skill, model mapping, review procedure, and agent definitions, and merges the owned model/agent config fields. ADHD files and instructions are untouched. Explicit model choices and available runtime capabilities still prevail.

Existing sessions do not automatically switch their main model. Follower machines do not run discovery. Usage records and credentials stay local.
