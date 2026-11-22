import sqlite3
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
import serbia_fts as fts


class SerbiaFTSTest(unittest.TestCase):
    def test_build_cache_is_content_addressed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            repo = root / fts.CORPUS
            repo.mkdir(parents=True)
            subprocess.run(['git', 'init', '-q', str(repo)], check=True)
            act = repo / 'zakon' / 'clan-1.md'
            act.parent.mkdir()
            act.write_text('Годишњи одмор', encoding='utf-8')

            def snapshot():
                subprocess.run(['git', 'add', '.'], cwd=repo, check=True)
                tree = subprocess.check_output(['git', 'write-tree'], cwd=repo, text=True).strip()
                return tree, (tree, dict(os.environ))

            with patch.object(fts.mcp, 'ROOT', root), patch.object(fts.mcp.law, '_store', return_value=root / 'cache'), patch.object(fts, 'snapshot', side_effect=snapshot), patch.object(fts, 'current_catalog', return_value=({}, '')):
                path = fts.build()
                with patch.object(fts, 'add_document', side_effect=AssertionError('must not reindex')):
                    self.assertEqual(fts.build(), path)
                    with self.assertRaises(AssertionError):
                        fts.build(force=True)
                    self.assertTrue(path.is_file())  # failed force must leave the old index intact
                with patch.object(fts, 'add_document', wraps=fts.add_document) as add:
                    self.assertEqual(fts.build(force=True), path)
                    self.assertTrue(add.called)
                act.write_text('Накнада штете', encoding='utf-8')
                new_path = fts.build()
                self.assertNotEqual(new_path, path)
                self.assertTrue(path.is_file())

    def test_serbian_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'fixture.sqlite3'
            rel = 'zakon/2011/72-3/clan-021.md'
            with sqlite3.connect(path) as db:
                fts.schema(db)
                fts.add_document(db, rel, 'blob', 'Састав судских већа\n# Члан 21.\nСастав суда', 0,
                                 {'zakon/2011/72-3': 'Законик о кривичном поступку'})
            q = fts.Query('sastav', path, 'rev')
            metadata = fts.Index().metadata(q, [rel])[rel]
            self.assertEqual(metadata['article'], '21')
            self.assertEqual(metadata['heading'], 'Члан 21.')
            self.assertEqual(metadata['heading_context'], 'Састав судских већа')
            self.assertEqual(metadata['act_kind'], 'zakon')
            self.assertEqual(metadata['publication_year'], 2011)
            self.assertEqual((metadata['issue'], metadata['item']), (72, 3))
            self.assertEqual(metadata['abbreviations'], ['zkp'])
            self.assertNotEqual(fts.index_path('a', 'first'), fts.index_path('a', 'second'))

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
                rowid = fts.add_document(db, 'a.md', 'blob-a', '\n\nГодишњи одмор', 0)
                body_b = 'Годишњи одмор\n\n\n\nГодишњи одмор траје'
                rowid = fts.add_document(db, 'b.md', 'blob-b', body_b, rowid)
                fts.add_document(db, 'c.md', 'blob-c', '\nСудског већа', rowid)
            hook = fts.Index()
            q = fts.Query('godisnji odmor', path, 'rev')
            self.assertEqual(hook.counts(q, [fts.CORPUS], False), {fts.CORPUS: 2})
            self.assertEqual(hook.paths(q, fts.CORPUS, 'a.md', 10), ['b.md'])
            self.assertEqual(hook.ranked(q, fts.CORPUS, 0, 10), ['b.md', 'a.md'])
            with patch.object(fts.mcp, 'read_blobs', return_value=[body_b]) as reader:
                self.assertEqual(hook.lines(q, fts.CORPUS, 'rev', ['b.md'], 1), {'b.md': [(1, 'Годишњи одмор')]})
                reader.assert_called_once_with(fts.mcp.ROOT / fts.CORPUS, ['blob-b'])
            self.assertIsNone(hook.lines(q, fts.CORPUS, 'old', ['b.md']))
            self.assertEqual(hook.paths(fts.Query('sudski', path, 'rev', True), fts.CORPUS, None, 10), ['c.md'])
            self.assertEqual(hook.counts('godisnji odmor', [fts.CORPUS], False), {})
            self.assertEqual(hook.counts(fts.Query('"OR"', path, 'rev'), [fts.CORPUS], False), {fts.CORPUS: 0})
