import sys
import tempfile
import unittest
from collections import OrderedDict
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
import mcp_server as mcp
import serbia_refs

SHA = '09019e8e6a8d73d50b8dfe9a647642cfe35761f7'
PATH = 'serbia/national/acts/zakon/2011/72-3/clan-021.md'
REPO = 'https://github.com/lexifina/serbia-law'


class SerbiaReferencesTest(unittest.TestCase):
    def call(self, name, args):
        response = mcp.handle({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                               'params': {'name': name, 'arguments': args}})['result']
        self.assertFalse(response['isError'], response.get('content'))
        return response['structuredContent']

    def test_law_details_preserves_trailers(self):
        data = self.call('law_details', {'commit': SHA, 'jurisdiction': 'serbia', 'include_diffs': False})
        change = data['changes'][0]
        self.assertEqual(change['commit_url'], f'{REPO}/commit/{SHA}')
        self.assertEqual(change['trailers']['In-force'], '2019-05-29')
        self.assertEqual(change['trailers']['Published'], '2019-05-21')
        self.assertIn('Source', change['trailers'])
        self.assertIn('Consolidated', change['trailers'])
        self.assertEqual(change['trailers_all']['In-force'], ['2019-05-29'])
        self.assertIn({'path': PATH, 'file_url': f'{REPO}/blob/{SHA}/zakon/2011/72-3/clan-021.md'}, change['provision_files'])

    def test_read_and_history(self):
        data = self.call('read_law', {'path': PATH, 'date': '2019-05-29'})
        self.assertEqual(data['file_url'], f'{REPO}/blob/{SHA}/zakon/2011/72-3/clan-021.md')
        self.assertEqual(data['last_change']['commit_url'], f'{REPO}/commit/{SHA}')
        self.assertEqual(data['last_change']['in_force'], '2019-05-29')
        self.assertTrue(data['cite']['official_url'])
        self.assert_no_extra_trailers(data)
        hist = self.call('provision_history', {'path': PATH})
        row = next(row for row in hist['changes'] if row['commit'] == SHA)
        self.assertEqual(row['commit_url'], f'{REPO}/commit/{SHA}')
        self.assertEqual(row['published'], '2019-05-21')
        self.assertEqual(row['file_url'], data['file_url'])
        self.assert_no_extra_trailers(hist)

    def assert_no_extra_trailers(self, obj):
        if isinstance(obj, dict):
            self.assertNotIn('trailers', obj)
            self.assertNotIn('trailers_all', obj)
            for value in obj.values():
                self.assert_no_extra_trailers(value)
        elif isinstance(obj, list):
            for value in obj:
                self.assert_no_extra_trailers(value)

    def test_dated_search_and_list(self):
        for date in ('2019-05-28', '2019-05-29', 'today'):
            read = self.call('read_law', {'path': PATH, 'date': date})
            expected = read['file_url']
            data = self.call('list_provisions', {'path': PATH.rsplit('/', 1)[0],
                                                'date': date, 'by_folder': False})
            row = next(r for r in data['provisions'] if r['path'] == PATH)
            self.assertEqual(row['file_url'], expected)
            self.assert_no_extra_trailers(data)
            results = self.call('search_law', {'query': 'суди у већу', 'date': date,
                                               'jurisdiction': PATH.rsplit('/', 1)[0]})
            row = next(r for r in results['results'] if r['path'] == PATH)
            self.assertEqual(row['file_url'], expected)
            self.assertEqual(row['version_commit'], read['version_commit'])
            self.assertEqual(row['last_change']['in_force'], read['last_change']['in_force'])
            self.assertEqual(row['last_change']['published'], read['last_change']['published'])
            self.assertEqual(row['last_change']['commit_url'], read['last_change']['commit_url'])
            self.assertEqual(row['sources'], read['sources'])
            if date == '2019-05-29':
                self.assertEqual({link['key'] for link in row['source_links']}, {'Source', 'Consolidated'})
            self.assert_no_extra_trailers(results)

    def test_source_batch_and_cache(self):
        sha1, sha2, missing = 'a' * 40, 'b' * 40, 'c' * 40
        body = b'tree ignored\n\nTitle\n\nSource: https://example.org/source\nConsolidated: https://example.org/version\n'
        with tempfile.TemporaryDirectory() as temp, patch.object(serbia_refs, '_source_cache', OrderedDict()), \
                patch.object(serbia_refs.law, '_store', return_value=Path(temp)), \
                patch.object(serbia_refs.law, '_cat_batch', return_value=[(b'commit', body), (b'commit', body), (b'missing', None)]) as batch:
            result = serbia_refs.sources_many([sha1, sha1, sha2, missing], mcp.links_from_body)
            self.assertEqual(batch.call_args.args[1], [sha1, sha2, missing])
            self.assertEqual(result[sha1], result[sha2])
            self.assertNotIn(missing, result)
            self.assertEqual(serbia_refs.sources_many([sha1, sha2], mcp.links_from_body), result)
            batch.assert_called_once()
            serbia_refs._source_cache.clear()
            self.assertEqual(serbia_refs.sources_many([sha1, sha2], mcp.links_from_body), result)
            batch.assert_called_once()  # disk cache is shared with upstream

    def test_compare_dates_links_changes(self):
        data = self.call('compare_dates', {'path': PATH, 'date_a': '2019-05-28', 'date_b': '2019-05-29'})
        self.assertEqual(data['changes'][0]['commit_url'], f'{REPO}/commit/{SHA}')
        self.assert_no_extra_trailers(data)

    def test_no_link_before_record(self):
        data = self.call('read_law', {'path': PATH, 'date': '1900-01-01'})
        self.assertNotIn('file_url', data)
        self.assert_no_extra_trailers(data)

    def test_read_many_and_discovery(self):
        expected = f'{REPO}/blob/{SHA}/zakon/2011/72-3/clan-021.md'
        data = self.call('read_law', {'paths': [PATH], 'date': '2019-05-29'})
        self.assertEqual(data['provisions'][0]['file_url'], expected)
        self.assertEqual(data['provisions'][0]['last_change']['commit_url'], f'{REPO}/commit/{SHA}')
        self.assert_no_extra_trailers(data)
        # Discovery links refer to the corpus pin, not an amending law; invalid
        # file paths are never given a link.
        _, found = serbia_refs.enrich('find_provision', '', {'results': [
            {'path': PATH}, {'path': PATH.replace('clan-021', 'does-not-exist')}]}, mcp.corpus_head)
        self.assertEqual(found['results'][0]['file_url'],
                         f'{REPO}/blob/{mcp.corpus_head(serbia_refs.CORPUS)}/zakon/2011/72-3/clan-021.md')
        self.assertNotIn('commit_url', found['results'][0])
        self.assertNotIn('file_url', found['results'][1])
        self.assert_no_extra_trailers(found)

    def test_nonserbian_scope_rejected(self):
        reply = mcp.handle({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                            'params': {'name': 'find_provision', 'arguments': {'query': '1', 'jurisdiction': 'germany'}}})
        self.assertTrue(reply['result']['isError'])

    def test_streamable_http(self):
        from starlette.testclient import TestClient
        from serbia_http import app
        with TestClient(app) as client:
            self.assertEqual(client.get('/health').status_code, 200)
            headers = {'Accept': 'application/json, text/event-stream'}
            result = client.post('/mcp', headers=headers, json={
                'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
                'params': {'protocolVersion': '2025-11-25', 'capabilities': {},
                           'clientInfo': {'name': 'test', 'version': '1'}}})
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json()['result']['serverInfo']['name'], 'serbia-law-mcp')
            discovery = client.post('/mcp', headers=headers, json={
                'jsonrpc': '2.0', 'id': 3, 'method': 'tools/list', 'params': {}})
            self.assertEqual(discovery.status_code, 200)
            tools = {t['name'] for t in discovery.json()['result']['tools']}
            self.assertIn('get_provision', tools)
            self.assertNotIn('check_precedent', tools)
            result = client.post('/mcp', headers=headers, json={
                'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call',
                'params': {'name': 'law_details', 'arguments': {'commit': SHA, 'include_diffs': False}}})
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json()['result']['structuredContent']['changes'][0]['commit_url'], f'{REPO}/commit/{SHA}')


if __name__ == '__main__':
    unittest.main()
