import copy
import json
import tempfile
import unittest
from pathlib import Path
from verify_results import read, verify_schedule, members_checked
import tarfile

HERE = Path(__file__).resolve().parent

class ScheduleTests(unittest.TestCase):
    def setUp(self):
        self.schedule = read(HERE / 'approved-sampling-plan.json')

    def test_linux_json_without_final_newline_matches_sealed_windows_json(self):
        linux_bytes = json.dumps(self.schedule, indent=2).encode()
        self.assertNotEqual(linux_bytes, (HERE / 'approved-sampling-plan.json').read_bytes())
        verify_schedule(json.loads(linux_bytes))

    def test_changed_image_rejected(self):
        self.schedule[0][0] = '0000000000000000'
        with self.assertRaises(ValueError): verify_schedule(self.schedule)

    def test_changed_order_rejected(self):
        self.schedule[0][0], self.schedule[0][1] = self.schedule[0][1], self.schedule[0][0]
        with self.assertRaises(ValueError): verify_schedule(self.schedule)

    def test_missing_step_rejected(self):
        with self.assertRaises(ValueError): verify_schedule(self.schedule[:-1])

    def test_corrupt_approved_reference_rejected(self):
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            p = Path(tmp) / 'corrupt.json'
            p.write_text(json.dumps(self.schedule), encoding='utf-8')
            with self.assertRaises(ValueError): verify_schedule(self.schedule, p)

    def test_archive_path_escape_rejected(self):
        class FakeTar:
            def getmembers(self):
                return [tarfile.TarInfo('output/rf-balanced-7805570/../../../escape')]
        with self.assertRaises(ValueError): members_checked(FakeTar(), '7805570')

if __name__ == '__main__': unittest.main()
