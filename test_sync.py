import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import sync


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.home = Path(self.temp.name) / "codex"
        self.source = Path(self.temp.name) / "shared"; self.original_shared = sync.SHARED
        shutil.copytree(sync.SHARED, self.source); sync.SHARED = self.source
    def tearDown(self):
        sync.SHARED = self.original_shared; self.temp.cleanup()
    def require(self, component):
        if not (self.source / component).is_dir(): self.skipTest(f"{component} package is not in this checkout")
    def args(self, *extra):
        import argparse
        components = [extra[i + 1] for i, value in enumerate(extra[:-1]) if value == "--component"]
        return argparse.Namespace(codex_home=str(self.home), check=False, update=False, adopt="--adopt" in extra, component=components, no_schedule=True)
    def sync_home(self, *extra): return sync.apply(self.args(*extra))

    def test_fresh_and_idempotent(self):
        self.assertEqual(self.sync_home(), 0)
        self.assertEqual(self.sync_home(), 0)
        if (self.source / "orchestration").is_dir():
            config = (self.home / "config.toml").read_text()
            model = json.loads((self.source / "orchestration/models.json").read_text())["coordinator"]["model"]
            self.assertIn(f'model = "{model}"', config)
            parsed = __import__("tomllib").loads(config)
            self.assertEqual(parsed["models"]["new_thread"]["model"], model)
            self.assertEqual(parsed["models"]["new_thread"]["model_reasoning_effort"], "low")
        if (self.source / "adhd").is_dir(): self.assertTrue((self.home / "skills/adhd-creative-flow/SKILL.md").exists())
        self.assertTrue((self.home / "model-routing/sync-state.json").exists())

    def test_preserves_unrelated_toml_and_agents(self):
        self.require("orchestration")
        self.home.mkdir(parents=True)
        (self.home / "config.toml").write_text('foo = "keep"\n[agents]\ncustom = 7\n')
        (self.home / "AGENTS.md").write_text("# My rules\nStay calm.\n")
        self.sync_home("--adopt")
        text = (self.home / "config.toml").read_text()
        self.assertIn('foo = "keep"', text); self.assertIn("custom = 7", text)
        agents = (self.home / "AGENTS.md").read_text()
        self.assertIn("Stay calm.", agents); self.assertEqual(agents.count("BEGIN:global-model-orchestration"), 1)

    def test_override_conflict_has_no_partial_mutation(self):
        self.home.mkdir(parents=True); (self.home / "AGENTS.override.md").write_text("mine")
        with self.assertRaises(sync.SyncError): self.sync_home()
        self.assertFalse((self.home / "config.toml").exists())

    def test_multiline_target_is_rejected(self):
        self.require("orchestration")
        self.home.mkdir(parents=True)
        (self.home / "config.toml").write_text('model = """\nbad\n"""\n')
        with self.assertRaises(sync.SyncError): self.sync_home("--adopt")
        self.assertNotIn("model_reasoning_effort", (self.home / "config.toml").read_text())

    def test_mapping_update_renders_agent(self):
        self.require("orchestration")
        self.sync_home()
        source = sync.SHARED / "orchestration/models.json"; original = source.read_text(); data = json.loads(original)
        original_catalog = sync.model_catalog
        try:
            data["coder"]["model"] = "gpt-5.6-terra"; source.write_text(json.dumps(data))
            sync.model_catalog = lambda: {'gpt-5.6-terra'}
            self.sync_home()
            self.assertIn('model = "gpt-5.6-terra"', (self.home / "agents/quota_coder.toml").read_text())
        finally:
            source.write_text(original)
            sync.model_catalog = original_catalog

    def test_missing_spark_and_astra_use_available_fallbacks(self):
        self.require("orchestration")
        original_catalog = sync.model_catalog
        sync.model_catalog = lambda: {'gpt-5.6-terra', 'gpt-5.6-luna'}
        try:
            self.sync_home()
        finally:
            sync.model_catalog = original_catalog
        mapping = json.loads((self.home / "model-routing/models.json").read_text())
        self.assertEqual(mapping['planner']['model'], 'gpt-5.6-terra')
        self.assertEqual(mapping['coder']['model'], 'gpt-5.6-luna')
        self.assertEqual(mapping['specialist']['model'], 'gpt-5.6-terra')
        self.assertIn('model = "gpt-5.6-terra"', (self.home / "agents/quota_planner.toml").read_text())
        self.assertIn('model = "gpt-5.6-luna"', (self.home / "agents/quota_coder.toml").read_text())
        self.assertIn('model = "gpt-5.6-terra"', (self.home / "agents/quota_specialist.toml").read_text())

    def test_schedule_failure_is_reported(self):
        original_catalog, original_schedule = sync.model_catalog, sync.install_schedule
        sync.model_catalog = lambda: None
        sync.install_schedule = lambda home: (_ for _ in ()).throw(sync.SyncError('scheduler unavailable'))
        try:
            args = self.args('--adopt'); args.no_schedule = False
            with self.assertRaisesRegex(sync.SyncError, 'scheduler unavailable'):
                sync.run(args)
        finally:
            sync.model_catalog, sync.install_schedule = original_catalog, original_schedule

    def test_adopt_installs_schedule(self):
        original_catalog, original_schedule = sync.model_catalog, sync.install_schedule
        scheduled = []
        sync.model_catalog = lambda: None
        sync.install_schedule = lambda home: scheduled.append(home)
        try:
            args = self.args('--adopt'); args.no_schedule = False
            self.assertEqual(sync.run(args), 0)
        finally:
            sync.model_catalog, sync.install_schedule = original_catalog, original_schedule
        self.assertEqual(scheduled, [self.home])

    def test_later_managed_edit_conflicts_without_partial_write(self):
        self.require("orchestration")
        self.sync_home(); config = self.home / "config.toml"
        model = json.loads((self.source / "orchestration/models.json").read_text())["coordinator"]["model"]
        config.write_text(config.read_text().replace(f'model = "{model}"', 'model = "mine"'))
        before = config.read_bytes()
        with self.assertRaises(sync.SyncError): self.sync_home()
        self.assertEqual(config.read_bytes(), before)

    def test_managed_symlink_is_rejected(self):
        self.require("orchestration")
        self.home.mkdir(parents=True); target = self.home / "elsewhere"
        target.write_text("keep")
        try: (self.home / "config.toml").symlink_to(target)
        except OSError: self.skipTest("Windows symlink privilege is unavailable")
        with self.assertRaises(sync.SyncError): self.sync_home()
        self.assertEqual(target.read_text(), "keep")

    def test_partial_keys_and_commented_header_keep_other_values(self):
        self.require("orchestration")
        self.home.mkdir(parents=True)
        (self.home / "config.toml").write_text('keep = [1, 2]\n[agents] # local\nenabled = false\ncustom = "yes"\n')
        self.sync_home("--adopt")
        data = __import__("tomllib").loads((self.home / "config.toml").read_text())
        self.assertEqual(data["keep"], [1, 2]); self.assertEqual(data["agents"]["custom"], "yes")
        self.assertTrue(data["agents"]["enabled"])

    def test_write_failure_rolls_back_and_keeps_unmanaged_log(self):
        routing = self.home / "model-routing"; routing.mkdir(parents=True)
        log = routing / "outcomes.jsonl"; log.write_text('{"event":"keep"}\n')
        original_atomic = sync.atomic
        def fail_agents(path, data):
            if path == self.home / "AGENTS.md": raise OSError("injected")
            return original_atomic(path, data)
        sync.atomic = fail_agents
        try:
            with self.assertRaises(OSError): self.sync_home()
        finally: sync.atomic = original_atomic
        self.assertFalse((self.home / "config.toml").exists())
        self.assertFalse((self.home / "AGENTS.md").exists())
        self.assertEqual(log.read_text(), '{"event":"keep"}\n')

    def test_fresh_adhd_only_never_touches_orchestration(self):
        self.require("adhd")
        if (self.source / "orchestration/models.json").exists(): (self.source / "orchestration/models.json").unlink()
        self.sync_home("--component", "adhd")
        self.assertTrue((self.home / "skills/adhd-creative-flow/SKILL.md").exists())
        self.assertFalse((self.home / "config.toml").exists())
        self.assertFalse((self.home / "model-routing/models.json").exists())
        self.assertFalse((self.home / "agents/quota_coder.toml").exists())
        self.assertNotIn("global-model-orchestration", (self.home / "AGENTS.md").read_text())
        state = json.loads((self.home / "model-routing/sync-state.json").read_text())
        self.assertEqual(state["components"], ["adhd"])
        self.assertIn("adhd", state["source_checkouts"]); self.assertNotIn("source_checkout", state)

    def test_fresh_orchestration_only_never_touches_adhd(self):
        self.require("orchestration")
        if (self.source / "adhd/instructions.md").exists(): (self.source / "adhd/instructions.md").unlink()
        self.sync_home("--component", "orchestration")
        self.assertTrue((self.home / "config.toml").exists())
        self.assertTrue((self.home / "model-routing/models.json").exists())
        self.assertFalse((self.home / "skills/adhd-creative-flow/SKILL.md").exists())
        self.assertNotIn("global-adhd-creative-design-agent", (self.home / "AGENTS.md").read_text())
        state = json.loads((self.home / "model-routing/sync-state.json").read_text())
        self.assertEqual(state["source_checkout"], str(sync.ROOT))

    def test_components_are_additive_and_default_syncs_installed_set(self):
        self.require("adhd"); self.require("orchestration")
        self.sync_home("--component", "adhd")
        self.sync_home("--component", "orchestration")
        self.assertTrue((self.home / "skills/adhd-creative-flow/SKILL.md").exists())
        self.assertTrue((self.home / "config.toml").exists())
        self.sync_home()
        self.assertEqual(json.loads((self.home / "model-routing/sync-state.json").read_text())["components"], ["adhd", "orchestration"])

    def test_sequential_standalone_defaults_install_both_components(self):
        self.require("adhd"); self.require("orchestration")
        adhd_source, orchestration_source = Path(self.temp.name) / "adhd-only", Path(self.temp.name) / "orchestration-only"
        shutil.copytree(self.source / "adhd", adhd_source / "adhd")
        shutil.copytree(self.source / "orchestration", orchestration_source / "orchestration")
        sync.SHARED = adhd_source; self.sync_home()
        sync.SHARED = orchestration_source; self.sync_home()
        self.assertTrue((self.home / "skills/adhd-creative-flow/SKILL.md").exists())
        self.assertTrue((self.home / "config.toml").exists())
        self.assertEqual(json.loads((self.home / "model-routing/sync-state.json").read_text())["components"], ["adhd", "orchestration"])

    def test_all_selects_every_available_component(self):
        self.sync_home("--component", "all")
        state = json.loads((self.home / "model-routing/sync-state.json").read_text())
        self.assertEqual(state["components"], [name for name in sync.COMPONENTS if (self.source / name).is_dir()])

    def test_unavailable_component_is_rejected(self):
        missing = "adhd" if not (self.source / "adhd").is_dir() else "orchestration"
        if (self.source / missing).is_dir(): shutil.rmtree(self.source / missing)
        with self.assertRaises(sync.SyncError): self.sync_home("--component", missing)

    def test_check_does_not_create_a_lock(self):
        args = self.args(); args.check = True
        self.assertEqual(sync.apply(args), 0)
        self.assertFalse((self.home / "model-routing/sync.lock").exists())

    def test_lock_conflict_reports_retry_later(self):
        with sync.sync_lock(self.home):
            result = subprocess.run([sys.executable, str(sync.ROOT / "sync.py"), "--codex-home", str(self.home)], text=True, capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("another sync is running; retry later", result.stderr)

    def test_orchestration_mapping_update_leaves_adhd_edit_alone(self):
        self.require("adhd"); self.require("orchestration")
        self.sync_home()
        adhd = self.home / "skills/adhd-creative-flow/SKILL.md"; adhd.write_text("mine")
        source = sync.SHARED / "orchestration/models.json"; original = source.read_text(); data = json.loads(original)
        try:
            data["coder"]["model"] = "new-coder"; source.write_text(json.dumps(data))
            self.sync_home("--component", "orchestration")
            self.assertEqual(adhd.read_text(), "mine")
            self.assertIn('model = "new-coder"', (self.home / "agents/quota_coder.toml").read_text())
        finally: source.write_text(original)

    def test_legacy_state_migrates_as_both_components(self):
        self.require("adhd"); self.require("orchestration")
        self.sync_home()
        state_path = self.home / "model-routing/sync-state.json"; state = json.loads(state_path.read_text())
        state["version"] = 1; state.pop("components"); state_path.write_text(json.dumps(state))
        self.sync_home()
        state = json.loads(state_path.read_text())
        self.assertEqual(state["version"], 2); self.assertEqual(state["components"], ["adhd", "orchestration"])

if __name__ == "__main__": unittest.main()
