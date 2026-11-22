import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))

import mcp_server as mcp
import serbia_profile

PATH = 'serbia/national/acts/zakon/2011/72-3/clan-021.md'
FOLDER = PATH.rsplit('/', 1)[0]
SHA = '09019e8e6a8d73d50b8dfe9a647642cfe35761f7'


class SerbiaProfileTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        serbia_profile.install()

    def call(self, name, args):
        result = mcp.handle({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                             'params': {'name': name, 'arguments': args}})['result']
        self.assertFalse(result['isError'], result.get('content'))
        return result['structuredContent']

    def test_localized_tools(self):
        tools = {t['name']: t for t in mcp.tool_list()}
        self.assertEqual(len(tools), 17)
        self.assertNotIn('world_on_date', tools)
        self.assertNotIn('check_precedent', tools)
        self.assertIn('Pronađi', tools['get_provision']['title'])
        self.assertNotIn('judgments', tools['search_law']['inputSchema']['properties']['kind']['enum'])

    def test_find_article_and_whole_act(self):
        for query in ('KZ čl. 246', 'Кривични законик члан 246'):
            found = self.call('find_provision', {'query': query})['results']
            self.assertEqual(found[0]['path'], 'serbia/national/acts/zakon/2005/85-30/tekst.md')
            self.assertTrue(found[0]['whole_act'])
        found = self.call('find_provision', {'query': 'cl. 21 st. 1 ZKP'})['results']
        self.assertEqual(found[0]['path'], PATH)

    def test_dated_citation(self):
        for citation, date in (('čl. 21 st. 1 ZKP', '2019-05-28'), ('ЗКП члан 21 став 1', '2019-05-29')):
            expected = self.call('read_law', {'path': PATH, 'date': date})
            got = self.call('get_provision', {'citation': citation, 'date': date})
            self.assertEqual(got['path'], PATH, got)
            self.assertEqual(got['file_url'], expected['file_url'])
            self.assertEqual(got['text'], expected['text'])
            self.assertEqual(got['requested']['paragraph'], 1)
            self.assertFalse(got['subdivision_verified'])
            self.assertTrue(got['cite']['official_url'])

    def test_exact_folder_and_unresolved(self):
        got = self.call('get_provision', {'law': FOLDER, 'article': 21, 'date': '2019-05-29', 'include_text': False})
        self.assertEqual(got['path'], PATH)
        self.assertIn(SHA, got['file_url'])
        got = self.call('get_provision', {'law': 'nepostojeći propis', 'article': 21})
        self.assertEqual(got['status'], 'unresolved')
        self.assertNotIn('file_url', got)

    def test_gazette_and_resolution(self):
        got = self.call('resolve_citations', {'text': 'чл. 21 ЗКП; Сл. гласник РС бр. 35/2019', 'date': '2019-05-29'})
        self.assertEqual(got['citations'][0]['path'], PATH)
        self.assertEqual(got['gazettes'][0]['issue'], '35/2019')
        got = self.call('search_changes', {'query': 'Sl. glasnik RS, br. 35/2019', 'jurisdiction': FOLDER})
        self.assertTrue(any(SHA.startswith(r.get('commit', 'x')) for r in got['changes']), got)


if __name__ == '__main__':
    unittest.main()
