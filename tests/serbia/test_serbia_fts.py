import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
import serbia_fts as fts


class SerbiaFTSTest(unittest.TestCase):
    def test_scripts_and_diacritics(self):
        self.assertEqual(fts.tokens('Годишњи одмор'), fts.tokens('godisnji odmor'))
        self.assertEqual(fts.tokens('грађанин'), fts.tokens('građanin'))
        self.assertEqual(fts.tokens('грађанин'), fts.tokens('gradjanin'))
        self.assertEqual(fts.tokens('судског', True), fts.tokens('sudski', True))

    def test_hooks_preserve_original_lines_and_revision(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'fixture.sqlite3'
            with sqlite3.connect(path) as db:
                fts.schema(db)
                rowid = fts.add_document(db, 'a.md', '\n\nГодишњи одмор', 0)
                rowid = fts.add_document(db, 'b.md', 'Годишњи одмор\n\n\n\nГодишњи одмор траје', rowid)
                fts.add_document(db, 'c.md', '\nСудског већа', rowid)
            hook = fts.Index()
            q = fts.Query('godisnji odmor', path, 'rev')
            self.assertEqual(hook.counts(q, [fts.CORPUS], False), {fts.CORPUS: 2})
            self.assertEqual(hook.paths(q, fts.CORPUS, 'a.md', 10), ['b.md'])
            self.assertEqual(hook.ranked(q, fts.CORPUS, 0, 10), ['b.md', 'a.md'])
            self.assertEqual(hook.lines(q, fts.CORPUS, 'rev', ['b.md'], 1), {'b.md': [(1, 'Годишњи одмор')]})
            self.assertIsNone(hook.lines(q, fts.CORPUS, 'old', ['b.md']))
            self.assertEqual(hook.paths(fts.Query('sudski', path, 'rev', True), fts.CORPUS, None, 10), ['c.md'])
            self.assertEqual(hook.counts('godisnji odmor', [fts.CORPUS], False), {})
            self.assertEqual(hook.counts(fts.Query('"OR"', path, 'rev'), [fts.CORPUS], False), {fts.CORPUS: 0})
