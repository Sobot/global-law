"""Add immutable references and original Git trailers to Serbian MCP responses."""
import os
import re
from urllib.parse import quote

import law

CORPUS = 'serbia/national/acts'
REPO = 'https://github.com/lexifina/serbia-law'
TOOLS = {'read_law', 'provision_history', 'compare_dates', 'law_details', 'laws_between',
         'search_changes', 'who_wrote', 'find_provision', 'list_provisions', 'search_law',
         'changes_between', 'world_on_date', 'phrase_history', 'resolve_citations', 'applies_to_case'}


def enabled():
    return os.environ.get('SERBIA_LAW_MCP') == '1'


def enrich(tool, text, data, args, commit_body, corpus_head):
    if tool not in TOOLS:
        return text, data
    links = []
    cache = {}
    cwd = law.corpus_dir(CORPUS)

    def refs(sha, path=None, trailers=True):
        if not isinstance(sha, str) or not re.fullmatch(r'[0-9a-fA-F]{7,40}', sha):
            return {}
        if sha not in cache:
            full = law.git('rev-parse', '--verify', f'{sha}^{{commit}}', cwd=cwd, check=False).strip()
            if not re.fullmatch(r'[0-9a-f]{40}', full):
                cache[sha] = {}
            else:
                cache[sha] = {'commit_url': f'{REPO}/commit/{full}'}
                if trailers:
                    all_values = law.trailers_all(commit_body(CORPUS, full))
                    cache[sha].update(trailers={k: v[0] for k, v in all_values.items()}, trailers_all=all_values)
        result = dict(cache[sha])
        if trailers and result and 'trailers_all' not in result:
            full = result['commit_url'].rsplit('/', 1)[-1]
            all_values = law.trailers_all(commit_body(CORPUS, full))
            result.update(trailers={k: v[0] for k, v in all_values.items()}, trailers_all=all_values)
            cache[sha].update(result)
        if result and path and path.startswith(CORPUS + '/') and path.endswith('.md'):
            full = result['commit_url'].rsplit('/', 1)[-1]
            rel = path[len(CORPUS) + 1:]
            # A renamed or removed file must never receive a guessed permalink.
            candidates = [rel]
            if law.git('cat-file', '-t', f'{full}:{rel}', cwd=cwd, check=False).strip() != 'blob':
                candidates = sorted(law._earlier_names(CORPUS, rel) - {rel})
            for candidate in candidates:
                if law.git('cat-file', '-t', f'{full}:{candidate}', cwd=cwd, check=False).strip() == 'blob':
                    result['file_url'] = f'{REPO}/blob/{full}/{quote(candidate, safe="/")}'
                    break
        return result

    def walk(obj, path=None, corpus=None):
        if isinstance(obj, list):
            for row in obj:
                walk(row, path, corpus)
        elif isinstance(obj, dict):
            path = obj.get('path') if isinstance(obj.get('path'), str) else path
            corpus = obj.get('corpus') if isinstance(obj.get('corpus'), str) else corpus
            if path and path.startswith(CORPUS + '/'):
                corpus = CORPUS
            sha = (obj.get('version_commit') if 'version_commit' in obj else
                   obj.get('commit') or obj.get('corpus_commit'))
            for key, value in list(obj.items()):
                if key not in ('trailers', 'trailers_all'):
                    walk(value, path, corpus)
            if corpus != CORPUS:
                return
            if sha and isinstance(sha, str):
                fields = refs(sha, path if obj.get('in_force') is not False and obj.get('in_record') is not False else None)
                obj.update(fields)
                if fields.get('file_url'):
                    links.append(fields['file_url'])
                if fields.get('commit_url'):
                    links.append(fields['commit_url'])
                if tool == 'law_details' and isinstance(obj.get('provisions'), list):
                    obj['provision_files'] = [{'path': p, 'file_url': url} for p in obj['provisions']
                                              if isinstance(p, str) and (url := refs(sha, p).get('file_url'))]
            elif obj.get('in_force') is not False and isinstance(obj.get('last_change'), dict):
                change = obj['last_change']
                if change.get('file_url'):
                    obj['file_url'] = change['file_url']
            elif tool in ('find_provision', 'list_provisions') and isinstance(obj.get('path'), str) and obj['path'].endswith('.md'):
                # Search/browse has no historical date. Link to the pinned corpus, but do not
                # describe that corpus-wide pin as the commit amending this provision.
                url = refs(corpus_head(CORPUS), path, trailers=False).get('file_url')
                if url:
                    obj['file_url'] = url
                    links.append(url)

    walk(data, args.get('path') if isinstance(args.get('path'), str) else None)
    if links:
        text += '\n\nGitHub reference (recorded versions and changes):\n' + '\n'.join(list(dict.fromkeys(links))[:20])
    return text, data
