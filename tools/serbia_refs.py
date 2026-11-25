"""Add GitHub permalinks and official sources using upstream legal metadata."""
from collections import OrderedDict
from hashlib import sha256
import os
import re
import tempfile
import threading
from urllib.parse import quote

import law

CORPUS = 'serbia/national/acts'
REPO = 'https://github.com/lexifina/serbia-law'
DETAIL_LINK_LIMIT = 60  # same bound as upstream's law_details diffs
SOURCE_CACHE_LIMIT = 4096
_source_cache = OrderedDict()
_source_lock = threading.Lock()
TOOLS = {'read_law', 'provision_history', 'compare_dates', 'law_details', 'laws_between',
         'search_changes', 'who_wrote', 'find_provision', 'list_provisions', 'search_law',
         'changes_between', 'resolve_citations', 'applies_to_case', 'read_version', 'compare_versions'}


def provision_path(path):
    return (isinstance(path, str) and path.startswith(CORPUS + '/') and path.endswith('.md')
            and '\n' not in path and '\r' not in path)


def sources_many(shas, parse_links):
    """Read only uncached commits in one Git batch; share upstream's immutable .msg cache."""
    out, missing = {}, []
    with _source_lock:
        for sha in dict.fromkeys(shas):
            if sha in _source_cache:
                out[sha] = _source_cache[sha]
                _source_cache.move_to_end(sha)
            else:
                missing.append(sha)
    if not missing:
        return out
    bodies, uncached = {}, []
    store = law._store() / 'blobs'
    for sha in missing:
        try:
            bodies[sha] = (store / sha[:2] / f'{sha}.msg').read_text(encoding='utf-8')
        except (OSError, UnicodeError):
            uncached.append(sha)
    if uncached:
        for sha, (kind, raw) in zip(uncached, law._cat_batch(law.corpus_dir(CORPUS), uncached)):
            if kind != b'commit' or raw is None or b'\n\n' not in raw:
                continue  # do not cache missing objects as empty sources
            # Do not populate the shared message cache with lossy decoding.
            try:
                body = raw.split(b'\n\n', 1)[1].decode('utf-8')
            except UnicodeDecodeError:
                continue
            bodies[sha] = body
            kept = store / sha[:2] / f'{sha}.msg'
            tmp = None
            try:
                kept.parent.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(dir=kept.parent, delete=False) as f:
                    tmp = f.name
                    f.write(body.encode('utf-8'))
                os.replace(tmp, kept)
            except OSError:
                pass  # an unwritable optional cache must not hide sources
            finally:
                if tmp:
                    try:
                        os.unlink(tmp)
                    except OSError:
                        pass
    parsed = {sha: tuple(parse_links(body)) for sha, body in bodies.items()}
    with _source_lock:
        for sha, info in parsed.items():
            _source_cache[sha] = info
            _source_cache.move_to_end(sha)
        while len(_source_cache) > SOURCE_CACHE_LIMIT:
            _source_cache.popitem(last=False)
    out.update(parsed)
    return out


def enrich(tool, text, data, corpus_head, parse_links=None):
    if tool not in TOOLS:
        return text, data
    links, pending = [], []
    shas, versions, changes = {}, {}, {}
    cwd = law.corpus_dir(CORPUS)

    def full_sha(sha):
        if not isinstance(sha, str) or not re.fullmatch(r'[0-9a-fA-F]{7,40}', sha):
            return None
        if sha not in shas:
            # The upstream version/change records already contain real commit hashes.
            # Only expand abbreviated hashes; never use a floating branch URL.
            full = sha.lower() if len(sha) == 40 else law.git(
                'rev-parse', '--verify', f'{sha}^{{commit}}', cwd=cwd, check=False).strip()
            shas[sha] = full if re.fullmatch(r'[0-9a-f]{40}', full) else None
        return shas[sha]

    def commit_ref(row, sha):
        if full := full_sha(sha):
            row['commit_url'] = f'{REPO}/commit/{full}'
            links.append(row['commit_url'])

    def file_ref(row, sha, path):
        if provision_path(path) and (full := full_sha(sha)):
            pending.append((row, full, path[len(CORPUS) + 1:]))

    def dated_ref(row, date, path):
        if not date or not provision_path(path):
            return
        key = (date, path)
        if key not in versions:
            versions[key] = law.file_commit(date, path)
        file_ref(row, versions[key], path)

    def read_ref(row):
        path = row.get('path')
        if not provision_path(path):
            return
        change = row.get('last_change') or {}
        sha = change.get('commit')
        if sha:
            commit_ref(change, sha)
        if row.get('in_force') is True and row.get('in_record') is not False:
            file_ref(row, row.get('version_commit') or sha, path)

    def change_refs(rows, path=None, files=False):
        for row in rows:
            if row.get('corpus') != CORPUS and not provision_path(row.get('path', path)):
                continue
            sha = row.get('commit') or row.get('corpus_commit')
            commit_ref(row, sha)
            if files and not (row.get('ended') or row.get('removes') or row.get('ends')
                              or ('blob' in row and row['blob'] is None)):
                file_ref(row, sha, row.get('path', path))

    if tool == 'read_law':
        for row in data.get('provisions', [data]):
            read_ref(row)
    elif tool == 'read_version':
        commit_ref(data, data.get('version_id'))
        file_ref(data, data.get('version_id'), data.get('path'))
    elif tool == 'compare_versions':
        for side in ('from', 'to'):
            row = data.get(side) or {}
            commit_ref(row, row.get('version_id'))
            file_ref(row, row.get('version_id'), row.get('path'))
    elif tool == 'law_details':
        for change in data.get('changes', []):
            if change.get('corpus') != CORPUS:
                continue
            sha = change.get('commit')
            commit_ref(change, sha)
            # Keep upstream's provisions list and original metadata unchanged.
            change['provision_files'] = []
            paths = change.get('provisions', [])
            if len(paths) > DETAIL_LINK_LIMIT:
                change['provision_files_truncated'] = True
            for path in paths[:DETAIL_LINK_LIMIT]:
                row = {'path': path}
                change['provision_files'].append(row)
                file_ref(row, sha, path)
    elif tool == 'find_provision':
        # No historical date: a discovery link, not the amending commit.
        for row in data.get('results', []):
            file_ref(row, corpus_head(CORPUS), row.get('path'))
    elif tool in ('search_law', 'list_provisions'):
        for row in data.get('results' if tool == 'search_law' else 'provisions', []):
            dated_ref(row, data.get('date'), row.get('path'))
        if tool == 'search_law':
            change_refs(data.get('related_changes', []))
    elif tool in ('provision_history', 'compare_dates', 'laws_between', 'search_changes'):
        change_refs(data.get('changes', []), data.get('path'), files=tool in ('provision_history', 'compare_dates'))
    elif tool == 'who_wrote':
        dated_ref(data, data.get('date'), data.get('path'))
    elif tool == 'resolve_citations':
        for row in data.get('citations', []):
            if row.get('status') == 'in force':
                dated_ref(row, data.get('date'), row.get('path'))
    elif tool == 'applies_to_case':
        if data.get('text'):
            dated_ref(data, data.get('text_date'), data.get('path'))
        for key in ('changes', 'later_changes_reaching_back'):
            change_refs(data.get(key, []), data.get('path'))
    elif tool == 'changes_between':
        for corpus in data.get('corpora', []):
            for row in corpus.get('provisions', []):
                if row.get('change') != 'removed':
                    dated_ref(row, data.get('date_b'), row.get('path'))

    def existing(pairs):
        # Use upstream's subprocess wrapper so deadlines and cancellation apply.
        pairs = list(dict.fromkeys(pairs))
        if not pairs:
            return {}
        done = law.subprocess.run(['git', 'cat-file', '--batch-check=%(objecttype) %(objectname)'], cwd=cwd,
                                  input=''.join(f'{sha}:{rel}\n' for sha, rel in pairs),
                                  capture_output=True, encoding='utf-8')
        if done.returncode or len(done.stdout.splitlines()) != len(pairs):
            return {}
        return {pair: info.split()[1] for pair, info in zip(pairs, done.stdout.splitlines()) if info.startswith('blob ')}

    def version_objects(pairs):
        # The first-parent comparison proves a text addition/change; merely existing at a
        # commit (e.g. a correction naming an unchanged file) does not prove a GitHub diff.
        return existing(pair for sha, rel in pairs for pair in (
            [(sha, rel)] if tool == 'find_provision' else [(sha, rel), (sha + '^1', rel)]))

    found = version_objects((sha, rel) for _, sha, rel in pending)
    # A provision may have moved: verify earlier names rather than guessing.
    alternatives = {(sha, rel): sorted(law._earlier_names(CORPUS, rel) - {rel})
                    for _, sha, rel in pending if (sha, rel) not in found}
    earlier = version_objects((sha, old) for (sha, _), names in alternatives.items() for old in names)
    dated_results = tool == 'search_law' and parse_links is not None
    verified = []
    for row, sha, rel in pending:
        if (sha, rel) not in found:
            rel = next((old for old in alternatives[sha, rel] if (sha, old) in earlier), None)
        if rel:
            row['file_url'] = f'{REPO}/blob/{sha}/{quote(rel, safe="/")}'
            links.append(row['file_url'])
            if tool != 'find_provision':
                commit_ref(row, sha)
                objects = found if (sha, rel) in found else earlier
                if objects.get((sha, rel)) != objects.get((sha + '^1', rel)):
                    # GitHub's diff anchor is SHA-256 of the unescaped repository-relative path.
                    row['file_diff_url'] = row['commit_url'] + '#diff-' + sha256(rel.encode('utf-8')).hexdigest()
                    links.append(row['file_diff_url'])
                    change = row.get('last_change')
                    if change and change.get('commit') == sha:
                        change['file_diff_url'] = row['file_diff_url']
            if dated_results:
                verified.append((row, sha))
    if verified:
        source_data = sources_many((sha for _, sha in verified), parse_links)
        official = []
        for row, sha in verified:
            path = row['path']
            key = (path, sha)
            if key not in changes:
                change = next((h for h in reversed(law.history(path)) if h['commit'] == sha), None)
                changes[key] = {k: change[k] for k in ('commit', 'law', 'kind', 'in_force', 'published', 'enacted',
                                'corrects', 'restates', 'credit_corrected_from') if k in change} if change else None
            row['version_commit'] = sha
            if changes[key] is not None:
                row['last_change'] = dict(changes[key])
                commit_ref(row['last_change'], sha)
                if 'file_diff_url' in row:
                    row['last_change']['file_diff_url'] = row['file_diff_url']
            else:
                commit_ref(row, sha)
            if sha in source_data:
                row['source_links'] = [dict(link) for link in source_data[sha]]
                row['sources'] = [link['url'] for link in source_data[sha]]
                official.extend(f"{sha} {link['key']}: {link['url']}" for link in source_data[sha])
        if official:
            text += '\n\nOfficial sources of recorded version commits (not necessarily the entire current act):\n' + '\n'.join(list(dict.fromkeys(official))[:20])
    if tool == 'law_details':
        for change in data.get('changes', []):
            if 'provision_files' in change:
                change['provision_files'] = [row for row in change['provision_files'] if 'file_url' in row]
    if links:
        text += '\n\nGitHub references (recorded versions and changes):\n' + '\n'.join(list(dict.fromkeys(links))[:20])
    return text, data
