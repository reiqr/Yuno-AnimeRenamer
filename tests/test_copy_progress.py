import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import file_operations as ops
import renamer_core as core


class CopyProgressTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='anime_copy_progress_')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'
        self.source.mkdir()
        self.output = self.root / 'output'
        self.history = self.root / 'history'
        self.storage_patch = patch.object(ops, '_storage', return_value=self.history)
        self.storage_patch.start()
        self.addCleanup(self.storage_patch.stop)

    def plan(self):
        return core.build_plan(
            str(self.source), '作品', 1, '{title} - {episode:02d}',
            mode='copy', output_folder=str(self.output))

    def test_copy_reports_byte_progress(self):
        data = b'a' * (2 * 1024 * 1024 + 137)
        (self.source / '03.mkv').write_bytes(data)
        events = []
        result = ops.execute_plan(self.plan(), lambda *args: events.append(args))
        self.assertTrue(result['ok'])
        self.assertTrue(events)
        byte_events = [event for event in events if len(event) >= 8]
        self.assertTrue(byte_events)
        last = byte_events[-1]
        self.assertEqual(last[3], len(data))
        self.assertEqual(last[4], len(data))
        self.assertEqual(last[5], len(data))
        self.assertEqual(last[6], len(data))
        self.assertGreaterEqual(last[7], 0)

    def test_cancel_copy_cleans_partial_output_and_keeps_source(self):
        data = b'b' * (4 * 1024 * 1024 + 23)
        source = self.source / '03.mkv'
        source.write_bytes(data)
        cancel = threading.Event()
        seen = []

        def progress(*args):
            seen.append(args)
            cancel.set()

        result = ops.execute_plan(self.plan(), progress, cancel)
        self.assertFalse(result['ok'])
        self.assertTrue(result.get('cancelled'))
        self.assertFalse(result.get('recovery_required'))
        self.assertEqual(source.read_bytes(), data)
        self.assertFalse(any(path.is_file() for path in self.output.rglob('*')))
        self.assertFalse(ops.pending_operation())
        self.assertTrue(seen)


if __name__ == '__main__':
    unittest.main()
