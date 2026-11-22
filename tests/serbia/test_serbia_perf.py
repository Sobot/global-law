import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
import serbia_perf


class SerbiaPerfTest(unittest.TestCase):
    def test_warm_budget_preserves_memory(self):
        for available, current, expected in ((1024, 400, 256), (600, 400, 88), (300, 400, 0), (1024, 1500, 0)):
            values = {'/proc/meminfo': f'MemAvailable: {available * 1024} kB\n',
                      '/sys/fs/cgroup/memory.max': str(1600 * serbia_perf.MIB),
                      '/sys/fs/cgroup/memory.current': str(current * serbia_perf.MIB)}
            with patch.object(Path, 'read_text', lambda p: values[str(p)]):
                self.assertEqual(serbia_perf.available_budget(), expected * serbia_perf.MIB)

    def test_pack_warm_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / 'example.idx').write_bytes(b'i' * 10)
            (directory / 'example.pack').write_bytes(b'p' * 100)
            (directory / 'ignored.txt').write_bytes(b'x' * 100)
            self.assertEqual(serbia_perf.read_packs(directory, 50), 50)
            self.assertEqual(serbia_perf.read_packs(directory, 500), 110)
            self.assertEqual(serbia_perf.read_packs(directory, 0), 0)
            self.assertEqual(serbia_perf.read_packs(directory, 500, seconds=0), 0)
