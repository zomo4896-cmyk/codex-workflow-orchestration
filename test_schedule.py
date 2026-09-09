import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import schedule


class ScheduleTests(unittest.TestCase):
    def test_systemd_quotes_paths_and_specifiers(self):
        self.assertEqual(schedule.systemd_quote('/a path/x%y$z'), '"/a path/x%%y$$z"')

    def test_current_platform_registration_without_side_effects(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {'XDG_CONFIG_HOME': tmp}):
                with patch('sys.argv', ['schedule.py', '--codex-home', tmp]):
                    with patch('schedule.subprocess.run') as run:
                        schedule.main()
            calls = [c.args[0] for c in run.call_args_list]
            self.assertIn('--check', calls[0])
            if os.name == 'nt':
                command = calls[1][-1]
                self.assertIn('pythonw.exe', command)
                self.assertIn('-RunLevel Limited', command)
                self.assertIn('-RepetitionInterval', command)
            else:
                label = '-'.join(name for name in ('adhd', 'orchestration') if (Path(schedule.__file__).parent / 'shared' / name).is_dir())
                unit = Path(tmp) / ('systemd/user/codex-sync-' + label + '.service')
                self.assertIn('--codex-home', unit.read_text())
                self.assertIn('--update', unit.read_text())
                self.assertEqual(calls[-1][:4], ['systemctl', '--user', 'enable', '--now'])


if __name__ == '__main__':
    unittest.main()
