import os
import sys
import unittest
from pathlib import Path

os.environ['GLOBAL_LAW_JURISDICTIONS'] = 'serbia'
os.environ['SERBIA_LAW_MCP'] = '1'
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
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
        self.assertEqual(data['trailers']['In-force'], '2019-05-29')
        hist = self.call('provision_history', {'path': PATH})
        row = next(row for row in hist['changes'] if row['commit'] == SHA)
        self.assertEqual(row['commit_url'], f'{REPO}/commit/{SHA}')
        self.assertEqual(row['trailers']['Published'], '2019-05-21')

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
            result = client.post('/mcp', headers=headers, json={
                'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call',
                'params': {'name': 'law_details', 'arguments': {'commit': SHA, 'include_diffs': False}}})
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json()['result']['structuredContent']['changes'][0]['commit_url'], f'{REPO}/commit/{SHA}')


if __name__ == '__main__':
    unittest.main()
