import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
import mcp_server as mcp
import serbia_profile as profile
from serbia_stemmer import phrase_pattern
from serbia_benchmark import citation_path, result_paths, score


class StemmerTest(unittest.TestCase):
    def pattern(self, query):
        return phrase_pattern(query, mcp.serbian_cyrillic, mcp.serbian_plain_pattern)

    def test_inflections_and_scripts(self):
        for query in ('naknada štete', 'naknada stete', 'накнада штете'):
            pattern = mcp.safe_regex(self.pattern(query))
            process = subprocess.run(['grep', '-E', '-i', pattern],
                                     input='Накнада штете\nнакнаду штетом\nнакнада штеточина\n',
                                     text=True, capture_output=True, check=True)
            self.assertEqual(process.stdout.splitlines(), ['Накнада штете', 'накнаду штетом'])
        self.assertIsNotNone(self.pattern('адаптација'))

    def test_unsupported(self):
        for query in ('чл. 21', 'a.*', 'one two three four', 'ZKP 21', ''):
            self.assertIsNone(self.pattern(query))

    def test_profile_opt_in(self):
        with patch.dict(profile._BASE, {'search_law': lambda args: ('law', {'args': args})}), \
             patch.object(mcp, 'scope_arg', return_value='serbia'):
            _, literal = profile.search_law({'query': 'naknada stete'})
            self.assertEqual(literal['args'], {'query': 'naknada stete'})
            _, expanded = profile.search_law({'query': 'naknada stete', 'morphology': True, 'date': '2019-05-29'})
            self.assertTrue(expanded['morphology_applied'])
            self.assertTrue(expanded['args']['regex'])
            self.assertEqual(expanded['args']['date'], '2019-05-29')
            with self.assertRaises(mcp.UserError):
                profile.search_law({'query': 'x', 'morphology': True, 'regex': True})

    def test_benchmark_mapping_and_metrics(self):
        files = ['zakon/2011/72-3/clan-021.md', 'zakon/2011/72-3/tekst.md']
        path = citation_path('sgrs/skupstina/zakon/2011/72/3::član 21', files)
        self.assertEqual(path, profile.CORPUS + '/' + files[0])
        self.assertIsNone(citation_path('ref/123::član 21', files))
        ranked = result_paths({'results': [{'path': 'x'}, {'path': 'x'}, {'path': path}]}, 2)
        self.assertEqual(score({path}, ranked), {'recall': 1.0, 'hit': 1, 'rr': 0.5})


if __name__ == '__main__':
    unittest.main()
