import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import serbia_http
import skill_resources


class SkillResourcesTest(unittest.IsolatedAsyncioTestCase):
    async def test_language_package_on_both_transports(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for language in ('en', 'sr'):
                entry = root / language / 'skills/example/SKILL.md'
                entry.parent.mkdir(parents=True)
                entry.write_text(f'# {language} — primer', encoding='utf-8')
            skills = skill_resources.load(root, 'sr')
            self.assertEqual(skill_resources.load(root, 'de'), {})

        server = serbia_http.upstream
        uri = 'skill://sr/example/SKILL.md'
        with patch.object(server, 'SKILLS', skills):
            def call(method, **params):
                return server.handle({'id': 1, 'method': method, 'params': params})['result']

            self.assertIn(uri, [r['uri'] for r in call('resources/list')['resources']])
            contents = call('resources/read', uri=uri)['contents'][0]
            self.assertEqual(contents['text'], '# sr — primer')
            self.assertEqual([str(r.uri) for r in await serbia_http.list_resources()], [uri])
            resource, = await serbia_http.read_resource(uri)
            self.assertEqual((resource.content, resource.mime_type), (contents['text'], contents['mimeType']))
            with self.assertRaises(ValueError):
                await serbia_http.read_resource('skill://en/example/SKILL.md')
