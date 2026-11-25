import sys
import os
import unittest
from pathlib import Path
from unittest.mock import patch

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
        self.assertEqual(len(tools), 19)
        self.assertNotIn('world_on_date', tools)
        self.assertNotIn('check_precedent', tools)
        self.assertIn('Pronađi', tools['get_provision']['title'])
        self.assertIn('tačnu verziju', tools['read_version']['title'])
        self.assertIn('tačne verzije', tools['compare_versions']['title'])
        self.assertEqual(tools['compare_versions']['inputSchema']['required'], ['path', 'from_version_id', 'to_version_id'])
        self.assertNotIn('judgments', tools['search_law']['inputSchema']['properties']['kind']['enum'])

    def test_find_article_and_whole_act(self):
        for query in ('KZ čl. 246', 'Кривични законик члан 246'):
            found = self.call('find_provision', {'query': query})['results']
            self.assertEqual(found[0]['path'], 'serbia/national/acts/zakon/2005/85-30/tekst.md')
            self.assertTrue(found[0]['whole_act'])
        found = self.call('find_provision', {'query': 'cl. 21 st. 1 ZKP'})['results']
        self.assertEqual(found[0]['path'], PATH)

    def test_dated_citation(self):
        versions = []
        for citation, date, revision in (('čl. 21 st. 1 ZKP', '2019-05-28', '4c9c5100'),
                                         ('ЗКП члан 21 став 1', '2019-05-29', '09019e8e')):
            expected = self.call('read_law', {'path': PATH, 'date': date})
            got = self.call('get_provision', {'citation': citation, 'date': date})
            versions.append(got['text'])
            self.assertEqual(got['path'], PATH, got)
            self.assertEqual(got['file_url'], expected['file_url'])
            self.assertIn(revision, got['file_url'])
            self.assertEqual(got['text'], expected['text'])
            self.assertEqual(got['requested']['paragraph'], 1)
            self.assertFalse(got['subdivision_verified'])
            self.assertTrue(got['cite']['official_url'])
        self.assertNotEqual(*versions)
        published = self.call('read_law', {'path': PATH, 'date': '2019-05-21'})
        self.assertEqual(published['text'], versions[0])

    def test_exact_version_tools_use_pinned_serbian_history(self):
        history = self.call('provision_history', {'path': PATH})['changes']
        self.assertGreaterEqual(len(history), 2)
        first, last = history[0], history[-1]
        exact = self.call('read_version', {'path': PATH, 'version_id': first['commit']})
        self.assertEqual(exact['path'], PATH)
        self.assertEqual(exact['version_id'], first['commit'])
        self.assertEqual(exact['in_force'], first['in_force'])
        self.assertTrue(exact['text_present'])
        self.assertTrue(exact['text'])
        self.assertIn(first['commit'], exact['commit_url'])
        self.assertIn(first['commit'], exact['file_url'])

        same = self.call('compare_versions', {'path': PATH, 'from_version_id': first['commit'],
                                              'to_version_id': first['commit']})
        self.assertTrue(same['unchanged'])
        self.assertTrue(all(part['op'] == 'same' for paragraph in same['paragraphs'] for part in paragraph))

        changed = self.call('compare_versions', {'path': PATH, 'from_version_id': first['commit'],
                                                 'to_version_id': last['commit']})
        self.assertEqual(changed['from']['version_id'], first['commit'])
        self.assertEqual(changed['to']['version_id'], last['commit'])
        self.assertIn(first['commit'], changed['from']['file_url'])
        self.assertIn(last['commit'], changed['to']['file_url'])
        self.assertGreater(len(changed['paragraphs']), 3)
        self.assertTrue(all(part['op'] in ('same', 'added', 'removed')
                            for paragraph in changed['paragraphs'] for part in paragraph))

    @patch.object(mcp, 'scope_arg', return_value='serbia')
    def test_missing_fts_falls_back_to_git_search(self, _scope):
        args = {'query': 'godišnji odmor', 'jurisdiction': 'serbia'}
        fallback = ('git result', {'results': [{'path': PATH}]})
        with patch.object(serbia_profile.serbia_fts, 'prepare', return_value=None) as prepare, \
             patch.dict(serbia_profile._BASE, {'search_law': lambda received: fallback}):
            self.assertEqual(serbia_profile._search_law(args), fallback)
            prepare.assert_called_once()
        with patch.object(serbia_profile.serbia_fts, 'prepare', side_effect=OSError('unreadable index')), \
             patch.dict(serbia_profile._BASE, {'search_law': lambda received: fallback}), \
             self.assertLogs('serbia_profile', level='WARNING') as logs:
            self.assertEqual(serbia_profile._search_law(args), fallback)
        self.assertIn('using Git search', logs.output[0])

    def test_zkp_article_26_before_record(self):
        path = FOLDER + '/clan-026.md'
        current = self.call('read_law', {'path': path, 'date': 'today'})
        self.assertTrue(current['in_force'])
        self.assertTrue(current['file_url'])
        self.assertTrue(current['cite']['official_url'])
        before = self.call('read_law', {'path': path, 'date': '2010-12-31'})
        self.assertIsNone(before['in_force'])
        self.assertFalse(before['in_record'])
        self.assertEqual(before['record_starts'], '2012-01-15')
        self.assertEqual(before['publication_year'], 2011)
        self.assertIn('not an enactment or commencement date', before['why'])
        self.assertIn('does not rule out retroactive effect', before['why'])
        self.assertIn('does not verify a predecessor', before['why'])
        self.assertNotIn('may well have been in force then', before['why'])
        self.assertNotIn('file_url', before)
        resolved = self.call('get_provision', {'citation': 'cl. 26 st. 1 ZKP', 'date': '2010-12-31'})
        self.assertEqual(resolved['path'], path)
        self.assertEqual(resolved['status'], 'unknown')
        self.assertEqual(resolved['why'], before['why'])
        same_year = self.call('read_law', {'path': path, 'date': '2011-01-01'})
        self.assertIsNone(same_year['in_force'])
        self.assertNotIn('publication_year', same_year)

    def test_empty_historical_search_warns_about_missing_coverage(self):
        result = self.call('search_law', {'query': 'Ако је кривично дело извршено на домаћем броду',
                                          'date': '2010-12-31', 'jurisdiction': 'serbia', 'max_results': 10})
        if result['page']['total'] == 0:
            self.assertTrue(any('ne dokazuje' in note for note in result['caveats']))
        with patch.object(serbia_profile, '_search_law',
                          return_value=('none', {'date': '2010-12-31', 'page': {'total': 0}, 'caveats': []})):
            text, empty = serbia_profile.search_law({'date': '2010-12-31'})
        self.assertIn('ne dokazuje', text)
        self.assertTrue(empty['caveats'])
        with patch.object(serbia_profile, '_search_law', return_value=('none', {'results': [], 'left_out': []})):
            text, empty = serbia_profile.search_law({'date': '1700-01-01'})
        self.assertIn('ne dokazuje', text)
        self.assertTrue(empty['caveats'])
        with patch.object(serbia_profile, '_search_law',
                          return_value=('found', {'date': '2010-12-31', 'page': {'total': 1}, 'caveats': []})):
            text, found = serbia_profile.search_law({'date': '2010-12-31', 'offset': 10})
        self.assertEqual(text, 'found')
        self.assertEqual(found['caveats'], [])

    def test_morphological_search_in_historical_article(self):
        result = self.call('search_law', {'query': 'sastava sudskog veca', 'morphology': True,
                                           'jurisdiction': PATH, 'date': '2019-05-29'})
        self.assertTrue(result['morphology_applied'])
        self.assertTrue(any(r['path'] == PATH and r.get('file_url') for r in result['results']), result)

    @unittest.skipUnless(os.environ.get('SERBIA_FTS_TEST') == '1', 'requires prebuilt FTS index')
    def test_current_fts_search(self):
        forms = ('годишњи одмор', 'godišnji odmor', 'godisnji odmor')
        results = [self.call('search_law', {'query': q, 'max_results': 5}) for q in forms]
        self.assertTrue(results[0]['results'])
        for got in results:
            self.assertEqual(got.get('search_backend'), 'sqlite_fts5')
            self.assertEqual(got['results'], results[0]['results'])
            self.assertTrue(all(r.get('file_url') for r in got['results']))
            self.assertTrue(all(r.get('version_commit') for r in got['results']))
        row = next(r for r in results[0]['results'] if r.get('sources'))
        read = self.call('read_law', {'path': row['path'], 'include_text': False})
        self.assertEqual(row['sources'], read['sources'])
        self.assertEqual(row['last_change']['in_force'], read['last_change']['in_force'])
        result = self.call('search_law', {'query': 'godisnjeg odmora', 'morphology': True, 'max_results': 5})
        self.assertEqual(result.get('search_backend'), 'sqlite_fts5')
        self.assertTrue(result['morphology_applied'])
        self.assertTrue(result['results'])

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
