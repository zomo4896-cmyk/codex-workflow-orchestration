from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


SCRIPT = Path(__file__).parent / "shared" / "orchestration" / "skills" / "workflow-model-orchestration" / "scripts" / "strategy.py"
SPEC = importlib.util.spec_from_file_location("orchestration_strategy", SCRIPT)
strategy = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(strategy)


MODELS = {
    "coordinator": {"model": "coord", "reasoning": "medium"},
    "routine": {"model": "routine", "reasoning": "max", "agent": "quota_routine"},
    "coder": {"model": "coder", "reasoning": "high", "agent": "quota_coder"},
    "planner": {"model": "planner", "reasoning": "medium", "agent": "quota_planner"},
    "specialist": {"model": "specialist", "reasoning": "xhigh", "agent": "quota_specialist"},
}


def task(node: str, role: str = "coder", depends_on: list[str] | None = None, reads: list[str] | None = None, writes: list[str] | None = None) -> dict:
    return {
        "id": node,
        "role": role,
        "depends_on": depends_on or [],
        "reads": reads or [],
        "writes": writes or [],
        "check": f"check {node}",
    }


def plan(tasks: list[dict], roles: list[str] | None = None, limit: int = 2, repair: dict | None = None) -> dict:
    value = {"tasks": tasks, "available_roles": roles if roles is not None else list(strategy.ROLES), "worker_limit": limit}
    if repair is not None:
        value["repair"] = repair
    return strategy.plan(value, MODELS)


class StrategyTests(unittest.TestCase):
    def test_windows_aliases_and_promotion_metadata(self) -> None:
        result = plan([task('a', writes=['Src/Value.py']), task('b', reads=['src/value.py'])])
        self.assertEqual(result['waves'], [['a'], ['b']])
        for scope in ['C:relative', 'src/*.py', 'src/value.py.']:
            with self.assertRaises(strategy.ValidationError):
                plan([task('a', writes=[scope])])
        spec = {'tasks': [task('a', role='coordinator')], 'available_roles': [], 'worker_limit': 0}
        self.assertEqual(strategy.plan(spec, dict(MODELS, _promotion_history=[]))['strategy'], 'direct')
        self.assertEqual(plan([task('a')], repair={'failed_node':'a','attempts':0,'cause':'external effect uncertain'})['loop']['decision'], 'reconcile')

    def test_cli_accepts_local_json_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            spec={'tasks':[task('a',role='coordinator')],'available_roles':[],'worker_limit':0}
            (folder/'plan.json').write_text(json.dumps(spec),encoding='utf-8')
            (folder/'models.json').write_text(json.dumps(MODELS),encoding='utf-8')
            done=subprocess.run([sys.executable,str(SCRIPT),'--plan',str(folder/'plan.json'),'--models',str(folder/'models.json')],capture_output=True,text=True)
            self.assertEqual(done.returncode,0,done.stderr)
            self.assertEqual(json.loads(done.stdout)['strategy'],'direct')

    def test_rejects_unknown_fields_duplicate_ids_and_missing_checks(self) -> None:
        cases = [
            {"tasks": [task("a")], "available_roles": [], "worker_limit": 1, "extra": True},
            {"tasks": [task("a"), task("a")], "available_roles": [], "worker_limit": 1},
            {"tasks": [{**task("a"), "check": ""}], "available_roles": [], "worker_limit": 1},
        ]
        for value in cases:
            with self.subTest(value=value), self.assertRaises(strategy.ValidationError):
                strategy.plan(value, MODELS)

    def test_rejects_unknown_dependencies_cycles_and_invalid_paths(self) -> None:
        cases = [
            [task("a", depends_on=["missing"])],
            [task("a", depends_on=["b"]), task("b", depends_on=["a"])],
            [task("a", writes=["../outside"])],
            [task("a", reads=["C:\\outside"])],
        ]
        for tasks in cases:
            with self.subTest(tasks=tasks), self.assertRaises(strategy.ValidationError):
                plan(tasks)

    def test_unavailable_role_and_zero_workers_use_coordinator_mapping(self) -> None:
        unavailable = plan([task("a")], roles=["routine"])
        zero = plan([task("a")], roles=["coder"], limit=0)
        for result in (unavailable, zero):
            self.assertEqual(result["assignments"]["a"]["model"], "coord")
            self.assertEqual(result["assignments"]["a"]["agent"], "coordinator")
            self.assertIn("routed to coordinator", result["assignments"]["a"]["reason"])

    def test_independent_fanout_is_bounded_to_two_workers(self) -> None:
        result = plan([task("a"), task("b"), task("c")])
        self.assertEqual(result["strategy"], "bounded_swarm")
        self.assertEqual(result["waves"], [["a", "b"], ["c"]])
        self.assertTrue(all(len(wave) <= 2 for wave in result["waves"]))

    def test_same_path_and_parent_directory_overlap_serialize(self) -> None:
        same = plan([task("a", writes=["src/value.py"]), task("b", reads=["src/value.py"])])
        parent = plan([task("a", writes=["src"]), task("b", reads=["src/value.py"])])
        for result in (same, parent):
            self.assertEqual(result["strategy"], "task_graph")
            self.assertEqual(result["waves"], [["a"], ["b"]])

    def test_read_only_overlap_can_fan_out(self) -> None:
        result = plan([task("a", reads=["src"]), task("b", reads=["src/value.py"])])
        self.assertEqual(result["waves"], [["a", "b"]])

    def test_dependency_graph_stages_ready_nodes(self) -> None:
        result = plan([task("map"), task("research", role="routine"), task("build", depends_on=["map", "research"])])
        self.assertEqual(result["strategy"], "task_graph")
        self.assertEqual(result["waves"], [["map", "research"], ["build"]])

    def test_planner_and_specialist_are_exclusive(self) -> None:
        result = plan([task("code"), task("decide", role="planner"), task("review", role="specialist")])
        self.assertEqual(result["waves"], [["decide"], ["review"], ["code"]])

    def test_retry_cap_and_operational_failures(self) -> None:
        retry = plan([task("a")], repair={"failed_node": "a", "attempts": 0, "cause": "test failure"})
        replan = plan([task("a")], repair={"failed_node": "a", "attempts": 1, "cause": "test failure"})
        blocked = plan([task("a")], repair={"failed_node": "a", "attempts": 0, "cause": "credentials unavailable"})
        reconcile = plan([task("a")], repair={"failed_node": "a", "attempts": 0, "cause": "external-effect-uncertain"})
        self.assertEqual(retry["loop"]["decision"], "retry")
        self.assertEqual(replan["loop"]["decision"], "replan")
        self.assertEqual(blocked["loop"]["decision"], "blocked")
        self.assertEqual(reconcile["loop"]["decision"], "reconcile")

    def test_context_reports_unknown_missing_files_and_current_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            self.assertEqual(strategy.context(home)["roles_status"], "unknown")
            routing = home / "model-routing"
            routing.mkdir()
            (routing / "models.json").write_text(json.dumps(MODELS), encoding="utf-8")
            (routing / "model-catalog.json").write_text(json.dumps({
                "schema_version": 1,
                "verified_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "sources": ["https://example.test/official"],
                "models": [{"id": "coord", "description": "configured model", "source": "https://example.test/official"}],
                "notice": "Catalog presence does not prove runtime access.",
            }), encoding="utf-8")
            result = strategy.context(home)
            self.assertEqual(result["roles_status"], "configured")
            self.assertEqual(result["roles"]["coder"]["reasoning"], "high")
            self.assertNotIn("agent", result["roles"]["coder"])
            self.assertEqual(result["model_catalog"]["status"], "current")
            catalog = json.loads((routing / "model-catalog.json").read_text(encoding="utf-8"))
            catalog["verified_at"] = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
            (routing / "model-catalog.json").write_text(json.dumps(catalog), encoding="utf-8")
            self.assertEqual(strategy.context(home)["model_catalog"]["status"], "source_refresh_due")

    def test_cli_prints_plan_json(self) -> None:
        spec = {"tasks": [task("a", role="coordinator")], "available_roles": [], "worker_limit": 0}
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "--plan", json.dumps(spec), "--models", json.dumps(MODELS)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["strategy"], "direct")


if __name__ == "__main__":
    unittest.main()
