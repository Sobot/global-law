"""Local, disposable FTS5 index of the Serbian text in force today."""
import hashlib
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import tempfile
import sys
from contextlib import closing, contextmanager
from functools import lru_cache

import mcp_server as mcp
from serbia_citations import normalize
from serbia_stemmer import stem

CORPUS = 'serbia/national/acts'
WORDS = re.compile(r'[^\W_]+', re.UNICODE)


@lru_cache(maxsize=32768)
def stem_token(token):
    cyr = mcp.serbian_cyrillic(token) or token
    return normalize(stem(cyr)[0])


def tokens(text, morphology=False):
    words = WORDS.findall(text.casefold())
    return ' '.join(stem_token(w) if morphology else normalize(w) for w in words)


@lru_cache(maxsize=1)
def version():
    digest = hashlib.sha256()
    for name in ('serbia_fts.py', 'serbia_citations.py', 'serbia_stemmer.py'):
        digest.update(Path(__file__).with_name(name).read_bytes())
    # Transliteration and file eligibility are shared with the upstream engine.
    digest.update(repr((mcp._SR_PAIRS, mcp._SR_ONE, mcp.NOT_LAW.pattern)).encode())
    return digest.hexdigest()[:20]


def snapshot():
    rev = mcp.tree_on(mcp.law.day('today'), CORPUS)
    if not rev:
        return None, None
    # Synthetic effective-date trees are stored in the upstream alternate object directory.
    env = {**os.environ}
    if mcp.law._TREES['dir'] is not None:
        alternate = str(mcp.law._tree_store() / 'objects')
        env['GIT_ALTERNATE_OBJECT_DIRECTORIES'] = alternate + (os.pathsep + env['GIT_ALTERNATE_OBJECT_DIRECTORIES'] if env.get('GIT_ALTERNATE_OBJECT_DIRECTORIES') else '')
    tree = subprocess.check_output(['git', 'rev-parse', f'{rev}^{{tree}}'], cwd=mcp.ROOT / CORPUS,
                                   env=env, text=True).strip()
    return rev, (tree, env)


def index_path(tree):
    return mcp.law._store() / 'serbia-fts' / f'{version()}-{tree}.sqlite3'


def connect(path):
    return sqlite3.connect(path.resolve().as_uri() + '?mode=ro&immutable=1', uri=True)


def schema(db):
    db.executescript('''
        CREATE TABLE documents(id INTEGER PRIMARY KEY, path TEXT NOT NULL UNIQUE, blob TEXT NOT NULL);
        CREATE TABLE lines(id INTEGER PRIMARY KEY, doc INTEGER NOT NULL, line INTEGER NOT NULL);
        CREATE VIRTUAL TABLE fts USING fts5(exact, roots, content='');
    ''')


def add_document(db, path, blob, body, rowid):
    doc = db.execute('INSERT INTO documents(path,blob) VALUES (?,?)', (path, blob)).lastrowid
    locations, searchable = [], []
    for n, line in enumerate(body.split('\n'), 1):
        if line.strip():
            rowid += 1
            locations.append((rowid, doc, n))
            searchable.append((rowid, tokens(line), tokens(line, True)))
    db.executemany('INSERT INTO lines VALUES (?,?,?)', locations)
    db.executemany('INSERT INTO fts(rowid,exact,roots) VALUES (?,?,?)', searchable)
    return rowid


@contextmanager
def build_lock(target):
    # Production and CI are Linux. Concurrent starts must not build the same index twice.
    try:
        import fcntl
    except ImportError:
        yield
        return
    with target.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def build():
    rev, snap = snapshot()
    if not rev:
        raise RuntimeError('No effective Serbian corpus')
    tree, env = snap
    target = index_path(tree)
    target.parent.mkdir(parents=True, exist_ok=True)
    with build_lock(target):
        return build_tree(target, tree, env)


def build_tree(target, tree, env):
    if target.is_file():
        print(f'Reusing FTS5 index: {target.name} ({target.stat().st_size} bytes)', flush=True)
        return target
    fd, name = tempfile.mkstemp(prefix=target.stem + '-building-', suffix='.sqlite3', dir=target.parent)
    os.close(fd)
    tmp = Path(name)
    cwd = mcp.ROOT / CORPUS
    try:
        listing = subprocess.check_output(['git', 'ls-tree', '-rz', tree], cwd=cwd, env=env)
        with sqlite3.connect(tmp) as db:
            db.execute('PRAGMA journal_mode=OFF')
            db.execute('PRAGMA synchronous=OFF')
            db.execute('PRAGMA cache_size=-32768')
            schema(db)
            rowid = 0
            proc = subprocess.Popen(['git', 'cat-file', '--batch'], cwd=cwd, env=env,
                                    stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            try:
                for entry in listing.split(b'\0'):
                    if not entry:
                        continue
                    meta, path = entry.split(b'\t', 1)
                    _, kind, blob = meta.split()
                    path = path.decode('utf-8')
                    if kind != b'blob' or not mcp.indexed_file(CORPUS, path):
                        continue
                    proc.stdin.write(blob + b'\n')
                    proc.stdin.flush()
                    header = proc.stdout.readline().split()
                    if len(header) != 3 or header[1] != b'blob':
                        raise RuntimeError(f'Cannot read blob {blob!r}')
                    body = proc.stdout.read(int(header[2])).decode('utf-8', 'replace')
                    if proc.stdout.read(1) != b'\n':
                        raise RuntimeError('Incomplete blob')
                    rowid = add_document(db, path, blob.decode('ascii'), body, rowid)
                proc.stdin.close()
                if proc.wait():
                    raise RuntimeError('git cat-file failed')
            finally:
                if proc.poll() is None:
                    proc.kill()
                    proc.wait()
                proc.stdout.close()
            db.execute("INSERT INTO fts(fts) VALUES ('optimize')")
            db.commit()
        tmp.chmod(0o644)
        os.replace(tmp, target)
        print(f'Built FTS5 index: {target.name} ({target.stat().st_size} bytes)', flush=True)
        return target
    finally:
        tmp.unlink(missing_ok=True)


class Query(str):
    """A validated request carrying its immutable index identity through upstream hooks."""
    def __new__(cls, text, path, revision, morphology=False):
        self = super().__new__(cls, text)
        self.path, self.revision, self.morphology = path, revision, morphology
        return self

    def strip(self, *args):
        return super().strip(*args) if args else self  # already validated and trimmed

    @property
    def match(self):
        return ('roots' if self.morphology else 'exact') + ':"' + tokens(self, self.morphology) + '"'


def prepare(text, morphology=False):
    if not WORDS.search(text):
        return None
    rev, snap = snapshot()
    if rev and (path := index_path(snap[0])).is_file():
        return Query(text, path, rev, morphology)
    return None


class Index:
    JOIN = ' FROM fts JOIN lines l ON l.id=fts.rowid JOIN documents d ON d.id=l.doc WHERE fts MATCH ?'

    def counts(self, query, corpora, case_law):
        if not isinstance(query, Query) or case_law or CORPUS not in corpora:
            return {}
        with closing(connect(query.path)) as db:
            return {CORPUS: db.execute('SELECT count(DISTINCT l.doc)' + self.JOIN, (query.match,)).fetchone()[0]}

    def paths(self, query, corpus, after, size):
        if not isinstance(query, Query) or corpus != CORPUS:
            return None
        with closing(connect(query.path)) as db:
            return [r[0] for r in db.execute('SELECT DISTINCT d.path' + self.JOIN + ' AND d.path > ? ORDER BY d.path LIMIT ?',
                                             (query.match, after or '', size))]

    def ranked(self, query, corpus, skip, size):
        if not isinstance(query, Query) or corpus != CORPUS:
            return None
        with closing(connect(query.path)) as db:
            return [r[0] for r in db.execute('SELECT d.path' + self.JOIN + ' GROUP BY d.path ORDER BY count(*) DESC, d.path LIMIT ? OFFSET ?',
                                             (query.match, size, skip))]

    def lines(self, query, corpus, revision, names, most=None):
        if not isinstance(query, Query) or corpus != CORPUS or revision != query.revision:
            return None
        rows = {name: [] for name in names}
        blobs = {}
        with closing(connect(query.path)) as db:
            marks = ','.join('?' for _ in names)
            for path, blob, line in db.execute('SELECT d.path,d.blob,l.line' + self.JOIN + f' AND d.path IN ({marks}) ORDER BY d.path,l.line',
                                                    (query.match, *names)):
                if most is None or len(rows[path]) < most:
                    rows[path].append(line)
                    blobs[path] = blob
        # Immutable Git blobs remain the source of truth; no duplicate original text in SQLite.
        bodies = mcp.read_blobs(mcp.ROOT / CORPUS, list(blobs.values()))
        if len(bodies) != len(blobs):
            return None
        for path, body in zip(blobs, bodies):
            lines = body.split('\n')
            if any(n > len(lines) for n in rows[path]):
                return None
            rows[path] = [(n, lines[n - 1]) for n in rows[path]]
        return rows


if __name__ == '__main__':
    if sys.argv[1:] == ['--key']:
        _, snap = snapshot()
        print(index_path(snap[0]).stem)
    else:
        build()
