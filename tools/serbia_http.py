"""Streamable HTTP adapter for the read-only Serbia Law MCP server."""
import os
import threading
import logging
import time
from contextlib import asynccontextmanager

os.environ['SERBIA_LAW_MCP'] = '1'
os.environ['GLOBAL_LAW_JURISDICTIONS'] = 'serbia'
os.environ['GLOBAL_LAW_HOSTED'] = '1'

import anyio
from mcp import types
from mcp.server.lowlevel.helper_types import ReadResourceContents
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

import mcp_server as upstream
import serbia_profile
import serbia_fts

serbia_profile.install()

server = Server('serbia-law-mcp', version='0.1.0', instructions=upstream.INSTRUCTIONS)
limiter = anyio.CapacityLimiter(1)  # upstream shares caches and processes calls in order


@server.list_resources()
async def list_resources():
    return [types.Resource.model_validate(r) for r in upstream.skill_resources.describe(upstream.SKILLS)]


@server.read_resource()
async def read_resource(uri):
    text = upstream.SKILLS.get(str(uri))
    if text is None:
        raise ValueError(f'Unknown resource {uri}')
    return [ReadResourceContents(content=text, mime_type='text/markdown')]


@server.list_tools()
async def list_tools():
    return [types.Tool.model_validate(t) for t in upstream.tool_list()]


@server.call_tool(validate_input=False)
async def call_tool(name, arguments):
    request = {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
               'params': {'name': name, 'arguments': arguments}}
    reply = await anyio.to_thread.run_sync(upstream.handle, request, limiter=limiter)
    if 'result' in reply:
        return types.CallToolResult.model_validate(reply['result'])
    return types.CallToolResult(isError=True, content=[types.TextContent(type='text', text=reply['error']['message'])])


manager = StreamableHTTPSessionManager(server, stateless=True, json_response=True)


class MCPEndpoint:
    async def __call__(self, scope, receive, send):
        await manager.handle_request(scope, receive, send)


async def health(request):
    ready = bool(upstream.corpus_head('serbia/national/acts'))
    return JSONResponse({'status': 'ok' if ready else 'not ready'}, status_code=200 if ready else 503)


@asynccontextmanager
async def lifespan(app):
    upstream.start_warming()
    def build_index():
        while True:
            try:
                serbia_fts.build()
            except Exception:
                logging.getLogger(__name__).exception('FTS5 index unavailable; using git search')
            # Future-effective provisions can change today's tree without a new Git pin.
            time.sleep(3600)
    threading.Thread(target=build_index, name='serbia-fts-build', daemon=True).start()
    async with manager.run():
        yield


app = Starlette(routes=[Route('/mcp', MCPEndpoint(), methods=['GET', 'POST', 'DELETE']),
                        Route('/health', health)], lifespan=lifespan)
