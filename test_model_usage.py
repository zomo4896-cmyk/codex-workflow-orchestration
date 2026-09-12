import json
import tempfile
import unittest
from pathlib import Path

from scripts.model_usage import inventory, summarize


def write_rollout(root, name, items, *, malformed=False):
    path = Path(root) / "2026" / "09" / f"rollout-{name}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(item) for item in items]
    if malformed:
        lines.insert(2, "{broken")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def meta(source="vscode"):
    return {"type": "session_meta", "timestamp": "2026-09-12T00:00:00Z", "payload": {"source": source}}


def turn(model, effort="medium", turn_id="turn-1"):
    return {
        "type": "turn_context",
        "timestamp": "2026-09-12T00:00:01Z",
        "payload": {"model": model, "effort": effort, "turn_id": turn_id},
    }


def usage(response_id, total, *, turn_id="turn-1", timestamp="2026-09-12T00:00:02Z", **values):
    counters = {
        "input_tokens": values.get("input_tokens", total - values.get("output_tokens", 0)),
        "cached_input_tokens": values.get("cached_input_tokens", 0),
        "output_tokens": values.get("output_tokens", 0),
        "reasoning_output_tokens": values.get("reasoning_output_tokens", 0),
        "total_tokens": total,
    }
    return {
        "type": "token_usage_record",
        "timestamp": timestamp,
        "payload": {"response_id": response_id, "turn_id": turn_id, "usage": counters},
    }


def legacy(last, total, *, timestamp="2026-09-12T00:00:02Z"):
    return {
        "type": "event_msg",
        "timestamp": timestamp,
        "payload": {"type": "token_count", "info": {"last_token_usage": last, "total_token_usage": total}},
    }


class ModelUsageTests(unittest.TestCase):
    def test_thread_source_classifies_automation_on_cache_hits(self):
        with tempfile.TemporaryDirectory() as tmp:
            header=meta('cli');header['payload']['thread_source']='automation'
            write_rollout(tmp,'auto',[header,turn('astra'),usage('auto-response',12)])
            cache=Path(tmp)/'cache.json'
            first=inventory(Path(tmp),cache_path=cache)
            second=inventory(Path(tmp),cache_path=cache)
            self.assertEqual(first['models'][0]['activity'],'automation')
            self.assertEqual(second['models'][0]['activity'],'automation')
            self.assertEqual(second['coverage']['cache_hits'],1)

    def test_per_response_usage_is_not_treated_as_cumulative(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_rollout(tmp, "x", [meta(), turn("luna"), usage("r1", 12), usage("r2", 20)])
            self.assertEqual(summarize(Path(tmp), 10), {"luna": (2, 32, 0)})

    def test_duplicate_response_last_snapshot_wins_across_files_and_turn_models_follow_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_rollout(tmp, "a", [meta(), turn("luna", "low", "t1"), usage("same", 10, turn_id="t1")])
            write_rollout(
                tmp,
                "b",
                [
                    meta(),
                    turn("luna", "low", "t1"),
                    usage("same", 14, turn_id="t1", timestamp="2026-09-12T00:00:03Z"),
                    turn("astra", "high", "t2"),
                    usage("r2", 21, turn_id="t2", reasoning_output_tokens=3),
                ],
            )
            result = inventory(Path(tmp))
            self.assertEqual(
                [(row["model"], row["effort"], row["responses"], row["total_tokens"]) for row in result["models"]],
                [("astra", "high", 1, 21), ("luna", "low", 1, 14)],
            )
            self.assertEqual(result["coverage"]["duplicate_response_records"], 1)

    def test_activity_ongoing_file_and_malformed_line_continuation(self):
        with tempfile.TemporaryDirectory() as tmp:
            worker = {"subagent": {"thread_spawn": {"agent_role": "quota_coder"}}}
            write_rollout(
                tmp,
                "open",
                [meta(worker), turn("sol", "high"), usage("r1", 9), usage("r2", 11)],
                malformed=True,
            )
            result = inventory(Path(tmp))
            self.assertEqual(result["coverage"]["malformed_lines"], 1)
            self.assertEqual(result["models"][0]["activity"], "worker")
            self.assertEqual(result["models"][0]["responses"], 2)

    def test_missing_counters_remain_distinct_from_zero_and_unknown_model_is_kept(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_rollout(
                tmp,
                "x",
                [
                    meta(),
                    {
                        "type": "token_usage_record",
                        "timestamp": "2026-09-12T00:00:02Z",
                        "payload": {"response_id": "r1", "usage": {"input_tokens": 0, "total_tokens": 0}},
                    },
                ],
            )
            row = inventory(Path(tmp))["models"][0]
            self.assertEqual(row["model"], "unknown")
            self.assertEqual(row["input_tokens"], 0)
            self.assertEqual(row["input_tokens_missing"], 0)
            self.assertIsNone(row["cached_input_tokens"])
            self.assertEqual(row["cached_input_tokens_missing"], 1)

    def test_legacy_deduplicates_snapshots_flags_reset_and_survives_mixed_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_rollout(
                tmp,
                "old",
                [
                    meta(),
                    turn("old-model", "low", "old"),
                    legacy({"total_tokens": 5}, {"total_tokens": 5}),
                    legacy({"total_tokens": 5}, {"total_tokens": 5}),
                    legacy({"total_tokens": 7}, {"total_tokens": 12}),
                    legacy({"total_tokens": 3}, {"total_tokens": 3}),
                    turn("new-model", "high", "new"),
                    legacy({"total_tokens": 4}, {"total_tokens": 7}),
                    usage("explicit", 4, turn_id="new"),
                ],
            )
            rows = inventory(Path(tmp))["models"]
            old = next(row for row in rows if row["model"] == "old-model")
            new = next(row for row in rows if row["model"] == "new-model")
            self.assertEqual((old["responses"], old["total_tokens"]), (3, 15))
            self.assertEqual(old["legacy_estimated_responses"], 3)
            self.assertEqual(old["legacy_uncertain_responses"], 1)
            self.assertEqual((new["responses"], new["total_tokens"], new["legacy_estimated_responses"]), (1, 4, 0))

    def test_cache_reuses_unchanged_stats_and_invalidates_changed_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "private-cache.json"
            path = write_rollout(tmp, "x", [meta(), turn("luna"), usage("r1", 4)])
            self.assertEqual(inventory(Path(tmp), cache)["coverage"]["cache_hits"], 0)
            self.assertEqual(inventory(Path(tmp), cache)["coverage"]["cache_hits"], 1)
            path.write_text(path.read_text(encoding="utf-8") + "\n" + json.dumps(usage("r2", 6)), encoding="utf-8")
            result = inventory(Path(tmp), cache)
            self.assertEqual(result["coverage"]["cache_hits"], 0)
            self.assertEqual(result["models"][0]["total_tokens"], 10)
            self.assertNotIn("r1", cache.read_text(encoding="utf-8"))
            self.assertNotIn("turn-1", cache.read_text(encoding="utf-8"))

    def test_inventory_has_no_recent_file_cap(self):
        with tempfile.TemporaryDirectory() as tmp:
            for index in range(101):
                write_rollout(tmp, str(index), [meta(), turn("luna"), usage(f"r{index}", 1)])
            result = inventory(Path(tmp))
            self.assertEqual(result["coverage"]["scanned_files"], 101)
            self.assertEqual(result["models"][0]["responses"], 101)


if __name__ == "__main__":
    unittest.main()
