"""Request-scoped timing for the Serbia HTTP deployment (no query text in logs)."""
import json
import logging
import threading
import time
from contextvars import ContextVar
from functools import wraps


_active = ContextVar('serbia_search_timing', default=None)
_log = logging.getLogger('uvicorn.error')


class Trace:
    def __init__(self):
        self.phases = {}
        self.lock = threading.Lock()

    def add(self, name, elapsed):
        with self.lock:
            ms, calls = self.phases.get(name, (0, 0))
            self.phases[name] = (ms + elapsed * 1000, calls + 1)

    def report(self):
        with self.lock:
            return {name: {'ms': round(ms, 2), 'calls': calls}
                    for name, (ms, calls) in self.phases.items()}


def timed(name, fn):
    @wraps(fn)
    def measured(*args, **kwargs):
        trace = _active.get()
        if trace is None:
            return fn(*args, **kwargs)
        start = time.perf_counter()
        try:
            return fn(*args, **kwargs)
        finally:
            trace.add(name, time.perf_counter() - start)
    return measured


def carry_timing(carry):
    """Propagate the shared recorder into upstream's search worker threads."""
    @wraps(carry)
    def carried(fn):
        run = carry(fn)
        trace = _active.get()
        if trace is None:
            return run

        @wraps(run)
        def measured(*args, **kwargs):
            token = _active.set(trace)
            try:
                return run(*args, **kwargs)
            finally:
                _active.reset(token)
        return measured
    return carried


def install(upstream, fts, refs):
    """Instrument the existing hooks without changing the FTS index identity."""
    if getattr(upstream, '_serbia_timing_installed', False):
        return
    upstream._serbia_timing_installed = True
    upstream.carried = carry_timing(upstream.carried)
    upstream.warmed = timed('startup_wait', upstream.warmed)
    upstream.tree_on = timed('effective_tree', upstream.tree_on)
    upstream.HANDLERS['search_law'] = timed('search_handler', upstream.HANDLERS['search_law'])
    upstream.t_search_law = timed('search_engine', upstream.t_search_law)
    fts.prepare = timed('index_prepare', fts.prepare)
    for method in ('counts', 'paths', 'ranked', 'lines', 'metadata'):
        index = upstream.search_index
        setattr(index, method, timed('fts_' + method, getattr(index, method)))
    upstream.read_blobs = timed('git_read_blobs', upstream.read_blobs)
    upstream.git_run = timed('git_commands', upstream.git_run)
    upstream.law.subprocess.run = upstream.git_run
    upstream.law.file_commit = timed('git_file_commit', upstream.law.file_commit)
    refs.enrich = timed('reference_enrichment', refs.enrich)


def run(handle, request, queued_at):
    if request['params']['name'] != 'search_law':
        return handle(request)
    trace = Trace()
    token = _active.set(trace)
    start = time.perf_counter()
    reply = None
    try:
        reply = handle(request)
        return reply
    finally:
        elapsed = time.perf_counter() - start
        _active.reset(token)
        result = (reply or {}).get('result', {})
        data = result.get('structuredContent') or {}
        record = {'backend': data.get('search_backend', 'git_or_unknown'),
                  'queue_ms': round((start - queued_at) * 1000, 2),
                  'handler_ms': round(elapsed * 1000, 2),
                  'error': not reply or 'error' in reply or bool(result.get('isError')),
                  'provision_count': data.get('provision_count'),
                  'returned_rows': len(data.get('results') or []),
                  'phases': trace.report()}
        _log.info('SERBIA_SEARCH_TIMING %s', json.dumps(record, separators=(',', ':')))
