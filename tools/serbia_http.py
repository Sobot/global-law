"""Streamable HTTP adapter for the read-only Serbia Law MCP server."""
import os
from contextlib import asynccontextmanager

os.environ['SERBIA_LAW_MCP'] = '1'
os.environ['GLOBAL_LAW_JURISDICTIONS'] = 'serbia'
os.environ['GLOBAL_LAW_HOSTED'] = '1'

import anyio
from mcp import types
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

import mcp_server as upstream

server = Server('serbia-law-mcp', version='0.1.0', instructions=upstream.INSTRUCTIONS)
limiter = anyio.CapacityLimiter(1)  # upstream shares caches and processes calls in order


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
    async with manager.run():
        yield


app = Starlette(routes=[Route('/mcp', MCPEndpoint(), methods=['GET', 'POST', 'DELETE']),
                        Route('/health', health)], lifespan=lifespan)
