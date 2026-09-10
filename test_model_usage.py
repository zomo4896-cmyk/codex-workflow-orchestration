import json
import tempfile
import unittest
from pathlib import Path

from scripts.model_usage import summarize


class ModelUsageTests(unittest.TestCase):
    def test_summarizes_usage_by_active_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "2026" / "09" / "rollout-x.jsonl"; path.parent.mkdir(parents=True)
            path.write_text("\n".join(json.dumps(item) for item in [
                {"type": "turn_context", "payload": {"model": "luna"}},
                {"type": "token_usage_record", "payload": {"usage": {"total_tokens": 12, "reasoning_output_tokens": 3}}},
                {"type": "turn_context", "payload": {"model": "astra"}},
                {"type": "token_usage_record", "payload": {"usage": {"total_tokens": 8, "reasoning_output_tokens": 4}}},
            ]))
            self.assertEqual(summarize(Path(tmp), 10), {"luna": (1, 12, 3), "astra": (1, 8, 4)})


if __name__ == "__main__":
    unittest.main()
