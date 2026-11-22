"""The Google ADK agent in adk/global_law reaches the server over stdio, and over Streamable HTTP when asked.
These need google-adk (Python 3.11+, requirements-adk.txt) and skip without it; they call no model."""
from __future__ import annotations

import asyncio
import importlib
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent

try:
    import google.adk  # noqa: F401
    HAVE_ADK = True
except ImportError:
    HAVE_ADK = False


@unittest.skipUnless(HAVE_ADK, 'needs google-adk: pip install -r requirements-adk.txt (Python 3.11+)')
class AdkAgent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(ROOT / 'adk'))
        sys.dont_write_bytecode = True

    def load(self, **env):
        with mock.patch.dict(os.environ, env):
            if 'GLOBAL_LAW_MCP_URL' not in env:
                os.environ.pop('GLOBAL_LAW_MCP_URL', None)
            for name in ('global_law.agent', 'global_law'):
                sys.modules.pop(name, None)
            return importlib.import_module('global_law.agent')

    def test_stdio_lists_and_calls_the_servers_tools(self):
        agent = self.load(GLOBAL_LAW_TEST_PASSED='1', GOOGLE_API_KEY='not passed on')
        params = agent.root_agent.tools[0]._connection_params
        self.assertIsInstance(params, agent.StdioConnectionParams)
        self.assertGreater(params.timeout, 120)  # longer than the server's own limit on a call
        self.assertEqual(params.server_params.env['GLOBAL_LAW_TEST_PASSED'], '1')
        self.assertNotIn('GOOGLE_API_KEY', params.server_params.env)

        async def run():
            toolset = agent.root_agent.tools[0]
            try:
                tools = {t.name: t for t in await toolset.get_tools()}
                answer = await tools['list_jurisdictions'].run_async(args={}, tool_context=None)
            finally:
                await toolset.close()
            return tools, answer

        old = os.getcwd()
        os.chdir(ROOT / 'tests')  # the server starts from the clone wherever the agent is run
        try:
            tools, answer = asyncio.run(run())
        finally:
            os.chdir(old)
        self.assertTrue({'list_jurisdictions', 'find_provision', 'read_law'} <= set(tools))
        self.assertTrue(answer['content'][0]['text'])

    def test_url_selects_streamable_http_and_model_is_configurable(self):
        agent = self.load(GLOBAL_LAW_MCP_URL='https://global-law.lexifina.com/mcp', GLOBAL_LAW_MODEL='gemini-test')
        params = agent.root_agent.tools[0]._connection_params
        self.assertIsInstance(params, agent.StreamableHTTPConnectionParams)
        self.assertEqual(params.url, 'https://global-law.lexifina.com/mcp')
        self.assertGreater(params.sse_read_timeout, 120)
        self.assertEqual(agent.root_agent.model, 'gemini-test')


if __name__ == '__main__':
    unittest.main()
