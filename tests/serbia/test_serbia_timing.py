import json
import sys
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
import serbia_timing as timing


class TimingTest(unittest.TestCase):
    def test_workers_and_nested_phases(self):
        worker = timing.carry_timing(lambda fn: fn)
        read = timing.timed('git_read_blobs', lambda: 'original')
        lookup = timing.timed('fts_lines', read)

        def handle(request):
            with ThreadPoolExecutor(2) as pool:
                run = worker(lookup)
                self.assertEqual([f.result() for f in (pool.submit(run), pool.submit(run))], ['original', 'original'])
            return {'result': {'structuredContent': {'search_backend': 'sqlite_fts5', 'provision_count': 435, 'results': [{}]}}}

        with self.assertLogs('uvicorn.error', level='INFO') as logs:
            reply = timing.run(handle, {'params': {'name': 'search_law', 'arguments': {'query': 'private-query'}}}, time.perf_counter())
        entry = json.loads(logs.output[0].split('SERBIA_SEARCH_TIMING ', 1)[1])
        self.assertEqual(reply['result']['structuredContent']['provision_count'], 435)
        self.assertEqual(entry['backend'], 'sqlite_fts5')
        self.assertEqual(entry['phases']['fts_lines']['calls'], 2)
        self.assertEqual(entry['phases']['git_read_blobs']['calls'], 2)
        self.assertNotIn('private-query', logs.output[0])
        self.assertIsNone(timing._active.get())

    def test_error_is_logged_and_context_reset(self):
        def fail(request):
            raise RuntimeError('failure')

        with self.assertLogs('uvicorn.error', level='INFO') as logs:
            with self.assertRaises(RuntimeError):
                timing.run(fail, {'params': {'name': 'search_law'}}, time.perf_counter())
        self.assertTrue(json.loads(logs.output[0].split('SERBIA_SEARCH_TIMING ', 1)[1])['error'])
        self.assertIsNone(timing._active.get())
