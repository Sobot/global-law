"""Add GitHub permalinks without duplicating upstream legal metadata."""
import re
from urllib.parse import quote

import law

CORPUS = 'serbia/national/acts'
REPO = 'https://github.com/lexifina/serbia-law'
DETAIL_LINK_LIMIT = 60  # same bound as upstream's law_details diffs
TOOLS = {'read_law', 'provision_history', 'compare_dates', 'law_details', 'laws_between',
         'search_changes', 'who_wrote', 'find_provision', 'list_provisions', 'search_law',
         'changes_between', 'resolve_citations', 'applies_to_case'}


def provision_path(path):
    return (isinstance(path, str) and path.startswith(CORPUS + '/') and path.endswith('.md')
            and '\n' not in path and '\r' not in path)


def enrich(tool, text, data, corpus_head):
    if tool not in TOOLS:
        return text, data
    links, pending = [], []
    shas, versions = {}, {}
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
        change_refs(data.get('changes', []), data.get('path'), files=tool == 'provision_history')
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
            return set()
        done = law.subprocess.run(['git', 'cat-file', '--batch-check=%(objecttype)'], cwd=cwd,
                                  input=''.join(f'{sha}:{rel}\n' for sha, rel in pairs),
                                  capture_output=True, encoding='utf-8')
        if done.returncode or len(done.stdout.splitlines()) != len(pairs):
            return set()
        return {pair for pair, kind in zip(pairs, done.stdout.splitlines()) if kind == 'blob'}

    found = existing((sha, rel) for _, sha, rel in pending)
    # A provision may have moved: verify earlier names rather than guessing.
    alternatives = {(sha, rel): sorted(law._earlier_names(CORPUS, rel) - {rel})
                    for _, sha, rel in pending if (sha, rel) not in found}
    earlier = existing((sha, old) for (sha, _), names in alternatives.items() for old in names)
    for row, sha, rel in pending:
        if (sha, rel) not in found:
            rel = next((old for old in alternatives[sha, rel] if (sha, old) in earlier), None)
        if rel:
            row['file_url'] = f'{REPO}/blob/{sha}/{quote(rel, safe="/")}'
            links.append(row['file_url'])
    if tool == 'law_details':
        for change in data.get('changes', []):
            if 'provision_files' in change:
                change['provision_files'] = [row for row in change['provision_files'] if 'file_url' in row]
    if links:
        text += '\n\nGitHub references (recorded versions and changes):\n' + '\n'.join(list(dict.fromkeys(links))[:20])
    return text, data
