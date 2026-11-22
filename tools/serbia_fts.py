"""Local, disposable FTS5 index of the Serbian text in force today."""
import hashlib
import json
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
from serbia_citations import ALIASES, article_number, normalize
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


@lru_cache(maxsize=2)
def catalog_metadata(pin):
    # Reuse the upstream title catalog; store a compact, exact projection only.
    titles = {folder: info.get('title', '') for folder, info in mcp.folder_titles(CORPUS, pin).items()}
    digest = hashlib.sha256(json.dumps(titles, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return titles, digest


def current_catalog():
    pin = mcp.corpus_head(CORPUS)
    return catalog_metadata(pin) if pin else ({}, '')


def index_path(tree, catalog_hash=''):
    identity = hashlib.sha256((version() + catalog_hash).encode()).hexdigest()[:20]
    return mcp.law._store() / 'serbia-fts' / f'{identity}-{tree}.sqlite3'


def connect(path):
    return sqlite3.connect(path.resolve().as_uri() + '?mode=ro&immutable=1', uri=True)


def schema(db):
    db.executescript('''
        CREATE TABLE acts(id INTEGER PRIMARY KEY, path TEXT NOT NULL UNIQUE, kind TEXT NOT NULL,
                          title TEXT, publication_year INTEGER, publication_key TEXT, gazette_prefix TEXT,
                          issue INTEGER, item INTEGER);
        CREATE TABLE act_aliases(act INTEGER NOT NULL, alias TEXT NOT NULL, PRIMARY KEY(alias, act));
        CREATE TABLE documents(id INTEGER PRIMARY KEY, path TEXT NOT NULL UNIQUE, blob TEXT NOT NULL,
                               act INTEGER NOT NULL, article TEXT, heading TEXT, heading_context TEXT);
        CREATE INDEX documents_article ON documents(act, article);
        CREATE INDEX acts_publication ON acts(publication_year, issue, item);
        CREATE TABLE lines(id INTEGER PRIMARY KEY, doc INTEGER NOT NULL, line INTEGER NOT NULL);
        CREATE VIRTUAL TABLE fts USING fts5(exact, roots, content='');
    ''')


def act_fields(path, titles):
    parent = path.rsplit('/', 1)[0] if '/' in path else path
    folder = parent if parent in titles or ('/' in parent and not re.fullmatch(r'\d{4}', parent.rsplit('/', 1)[-1])) else path
    kind = path.split('/', 1)[0]
    parts = folder.split('/')
    year, key, prefix, issue, item = None, None, None, None, None
    # Preserve the publisher's raw identifier. Numeric components are only
    # parsed from the recognizable national/municipal folder convention.
    if len(parts) >= 3 and re.fullmatch(r'\d{4}', parts[-2]):
        year, key = int(parts[-2]), parts[-1]
        match = re.fullmatch(r'([a-z]*)(\d+)-(\d+)', key)
        if match:
            prefix, issue, item = match[1] or None, int(match[2]), int(match[3])
    return folder, kind, titles.get(folder), year, key, prefix, issue, item


def add_document(db, path, blob, body, rowid, titles=None):
    fields = act_fields(path, titles or {})
    db.execute('INSERT OR IGNORE INTO acts(path,kind,title,publication_year,publication_key,gazette_prefix,issue,item) VALUES (?,?,?,?,?,?,?,?)', fields)
    act = db.execute('SELECT id FROM acts WHERE path=?', (fields[0],)).fetchone()[0]
    if fields[2]:
        title_key = normalize(fields[2])
        db.executemany('INSERT OR IGNORE INTO act_aliases VALUES (?,?)',
                       ((act, alias) for alias, name in ALIASES.items() if normalize(name) == title_key))
    match = re.fullmatch(r'clan-(\d+(?:-?[a-z])?)\.md', path.rsplit('/', 1)[-1])
    article = article_number(match[1]) if match else None
    heading, context, previous = None, None, None
    for line in body.split('\n'):
        if line.startswith('#'):
            heading = line.lstrip('#').strip()[:300]
            # The previous line may be a title or a section label, not necessarily an official article title.
            context = previous if article else None
            break
        if line.strip():
            previous = line.strip()[:300]
    doc = db.execute('INSERT INTO documents(path,blob,act,article,heading,heading_context) VALUES (?,?,?,?,?,?)',
                     (path, blob, act, article, heading, context)).lastrowid
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


def build(force=False):
    rev, snap = snapshot()
    if not rev:
        raise RuntimeError('No effective Serbian corpus')
    tree, env = snap
    titles, catalog_hash = current_catalog()
    target = index_path(tree, catalog_hash)
    target.parent.mkdir(parents=True, exist_ok=True)
    before = target.stat().st_ino if target.is_file() else None
    with build_lock(target):
        # A concurrent startup build may already have satisfied a forced request.
        if force and target.is_file() and target.stat().st_ino != before:
            force = False
        return build_tree(target, tree, env, titles, force)


def build_tree(target, tree, env, titles, force=False):
    if target.is_file() and not force:
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
                    rowid = add_document(db, path, blob.decode('ascii'), body, rowid, titles)
                proc.stdin.close()
                if proc.wait():
                    raise RuntimeError('git cat-file failed')
            finally:
                if proc.poll() is None:
                    proc.kill()
                    proc.wait()
                proc.stdin.close()
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
    if rev and (path := index_path(snap[0], current_catalog()[1])).is_file():
        return Query(text, path, rev, morphology)
    return None


class Index:
    JOIN = ' FROM fts JOIN lines l ON l.id=fts.rowid JOIN documents d ON d.id=l.doc WHERE fts MATCH ?'

    def metadata(self, query, names):
        if not names:
            return {}
        with closing(connect(query.path)) as db:
            marks = ','.join('?' for _ in names)
            result = {path: {k: v for k, v in zip(('act_path', 'act_kind', 'act_title', 'publication_year',
                     'publication_key', 'gazette_prefix', 'issue', 'item', 'article', 'heading', 'heading_context', 'abbreviations'), values) if v is not None}
                    for path, *values in db.execute('SELECT d.path,a.path,a.kind,a.title,a.publication_year,a.publication_key,'
                    'a.gazette_prefix,a.issue,a.item,d.article,d.heading,d.heading_context,'
                    '(SELECT group_concat(alias) FROM act_aliases WHERE act=a.id) FROM documents d JOIN acts a ON d.act=a.id '
                    f'WHERE d.path IN ({marks})', names)}
            for row in result.values():
                if 'abbreviations' in row:
                    row['abbreviations'] = row['abbreviations'].split(',')
                if 'publication_key' in row:
                    row['publication_reference_source'] = 'repository_path'
            return result

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
        print(index_path(snap[0], current_catalog()[1]).stem)
    elif sys.argv[1:] == ['--force']:
        build(force=True)
    else:
        build()
