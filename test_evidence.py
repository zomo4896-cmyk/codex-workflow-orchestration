from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parent / "shared" / "orchestration" / "skills" / "workflow-model-orchestration" / "scripts" / "evidence.py"


class CliMixin:
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_cli(self, *arguments: str) -> tuple[int, dict]:
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), *arguments],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.stderr, "")
        return completed.returncode, json.loads(completed.stdout)

    def manifest(self, root: Path, files: list[dict], git_scope: dict | None = None) -> Path:
        value = {"root": str(root.resolve()), "files": files}
        if git_scope is not None:
            value["git_scope"] = git_scope
        path = self.directory / "manifest.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    @staticmethod
    def entry(path: Path, relative: str, file_format: str | None = None) -> dict:
        value = {"path": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        if file_format:
            value["format"] = file_format
        return value

    def test_hash_and_format_failures(self) -> None:
        root = self.directory / "root"
        root.mkdir()
        bad_json = root / "bad.json"
        bad_toml = root / "bad.toml"
        mismatch = root / "mismatch.txt"
        bad_json.write_text("{", encoding="utf-8")
        bad_toml.write_text("value = [", encoding="utf-8")
        mismatch.write_text("value", encoding="utf-8")
        entries = [
            {"path": "mismatch.txt", "sha256": "0" * 64},
            self.entry(bad_json, "bad.json", "json"),
            self.entry(bad_toml, "bad.toml", "toml"),
        ]
        code, result = self.run_cli("verify", "--manifest", str(self.manifest(root, entries)))
        self.assertEqual(code, 1)
        self.assertFalse(result["passed"])
        self.assertEqual({failure["error"] for failure in result["failures"]}, {"sha256 mismatch", "invalid JSON", "invalid TOML"})

    def test_unhashable_field_values_are_reported_as_json(self) -> None:
        root = self.directory / "root"
        root.mkdir()
        target = root / "value.json"
        target.write_text("{}", encoding="utf-8")
        entry = self.entry(target, "value.json")
        entry["format"] = []
        code, result = self.run_cli("verify", "--manifest", str(self.manifest(root, [entry])))
        self.assertEqual(code, 1)
        self.assertEqual(result["failures"][0]["error"], "format must be json or toml")

        outcome_path = self.directory / "outcomes.jsonl"
        outcome_path.write_text(json.dumps({
            "utc": "2026-09-10T00:00:00Z",
            "category": "coding",
            "outcome": [],
            "coordinator_model": None,
            "worker_models": [],
            "rework_cycles": 0,
            "escalation_reason": None,
            "verification": "none",
            "incompatibility": None,
        }) + "\n", encoding="utf-8")
        code, result = self.run_cli("outcomes", "--path", str(outcome_path))
        self.assertEqual(code, 1)
        self.assertEqual(result["errors"], [{"line": 1, "error": "invalid outcome record"}])

        nul_manifest = self.directory / "nul-manifest.json"
        nul_manifest.write_text(json.dumps({
            "root": str(root.resolve()) + "\0",
            "files": [self.entry(target, "value.json")],
        }), encoding="utf-8")
        code, result = self.run_cli("verify", "--manifest", str(nul_manifest))
        self.assertEqual(code, 1)
        self.assertEqual(result["failures"], [{"check": "manifest", "error": "root is missing or inaccessible"}])

    def test_rejects_traversal_and_escaping_symlink(self) -> None:
        root = self.directory / "root"
        root.mkdir()
        outside = self.directory / "outside.json"
        outside.write_text("{}", encoding="utf-8")
        traversal = self.entry(outside, "../outside.json", "json")
        code, result = self.run_cli("verify", "--manifest", str(self.manifest(root, [traversal])))
        self.assertEqual(code, 1)
        self.assertIn("remain under root", result["failures"][0]["error"])

        link = root / "link.json"
        try:
            os.symlink(outside, link)
        except (OSError, NotImplementedError):
            return
        code, result = self.run_cli("verify", "--manifest", str(self.manifest(root, [self.entry(link, "link.json", "json")])))
        self.assertEqual(code, 1)
        self.assertEqual(result["failures"][0]["error"], "file resolves outside root")

    def test_outcomes_normalizes_legacy_and_reports_line_without_content(self) -> None:
        path = self.directory / "outcomes.jsonl"
        legacy = {
            "date": "2026-09-10",
            "category": "coding",
            "outcome": "verified",
            "coordinator_model": None,
            "worker_models": [None, "worker-1"],
            "rework_cycles": 0,
            "escalation_reason": None,
            "verification": ["unit tests", "CLI smoke"],
            "incompatibility": None,
        }
        invalid = {**legacy, "date": "2026-09-11", "secret-field": "must-not-appear"}
        path.write_text(json.dumps(legacy) + "\n" + json.dumps(invalid) + "\n", encoding="utf-8")
        code, result = self.run_cli("outcomes", "--path", str(path), "--limit", "100")
        self.assertEqual(code, 1)
        self.assertEqual(result["records"][0]["utc"], "2026-09-10T00:00:00Z")
        self.assertEqual(result["records"][0]["verification"], "unit tests; CLI smoke")
        self.assertEqual(result["records"][0]["worker_models"], [None, "worker-1"])
        self.assertEqual(result["errors"], [{"line": 2, "error": "invalid outcome record"}])
        self.assertNotIn("must-not-appear", json.dumps(result))

    def test_legacy_missing_coordinator_stays_unknown(self) -> None:
        path = self.directory / "outcomes.jsonl"
        path.write_text(json.dumps({
            "utc": "2026-09-10T08:30:00+08:00",
            "category": "coding",
            "outcome": "partial",
            "worker_models": [],
            "rework_cycles": 1,
            "escalation_reason": None,
            "verification": "focused checks",
            "incompatibility": None,
        }) + "\n", encoding="utf-8")
        code, result = self.run_cli("outcomes", "--path", str(path))
        self.assertEqual(code, 0)
        self.assertEqual(result["records"][0]["utc"], "2026-09-10T00:30:00Z")
        self.assertIsNone(result["records"][0]["coordinator_model"])


class EvidenceCliTests(CliMixin, unittest.TestCase):
    pass


@unittest.skipUnless(shutil.which("git"), "git is required")
class GitScopeTests(CliMixin, unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.repository = self.directory / "repo"
        self.repository.mkdir()
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Evidence Test")
        (self.repository / "allowed.txt").write_text("allowed\n", encoding="utf-8")
        (self.repository / "other.txt").write_text("original\n", encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-qm", "base")

    def git(self, *arguments: str) -> None:
        subprocess.run(["git", *arguments], cwd=self.repository, check=True, capture_output=True)

    def scoped_manifest(self, allowed: list[str]) -> Path:
        return self.manifest(
            self.repository,
            [self.entry(self.repository / "allowed.txt", "allowed.txt")],
            {"base": "HEAD", "allowed": allowed},
        )

    def test_rejects_outside_scope_tracked_change(self) -> None:
        (self.repository / "other.txt").write_text("changed\n", encoding="utf-8")
        code, result = self.run_cli("verify", "--manifest", str(self.scoped_manifest(["allowed.txt"])))
        self.assertEqual(code, 1)
        self.assertEqual(result["failures"][-1]["paths"], ["other.txt"])

    def test_rejects_staged_change_undone_in_worktree(self) -> None:
        (self.repository / "other.txt").write_text("staged\n", encoding="utf-8")
        self.git("add", "other.txt")
        (self.repository / "other.txt").write_text("original\n", encoding="utf-8")
        code, result = self.run_cli("verify", "--manifest", str(self.scoped_manifest(["allowed.txt"])))
        self.assertEqual(code, 1)
        self.assertEqual(result["failures"][-1]["paths"], ["other.txt"])

    def test_rejects_outside_scope_untracked_file(self) -> None:
        (self.repository / "extra.txt").write_text("new\n", encoding="utf-8")
        code, result = self.run_cli("verify", "--manifest", str(self.scoped_manifest(["allowed.txt"])))
        self.assertEqual(code, 1)
        self.assertEqual(result["failures"][-1]["paths"], ["extra.txt"])

    def test_no_renames_requires_both_paths(self) -> None:
        (self.repository / "other.txt").rename(self.repository / "renamed.txt")
        self.git("add", "-A")
        code, result = self.run_cli("verify", "--manifest", str(self.scoped_manifest(["allowed.txt", "renamed.txt"])))
        self.assertEqual(code, 1)
        self.assertEqual(result["failures"][-1]["paths"], ["other.txt"])


if __name__ == "__main__":
    unittest.main()
