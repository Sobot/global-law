"""Offline retrieval benchmark over srb-legal-rag's external CC BY 4.0 goldens.

This measures retrieval of article paths, not legal-answer correctness.
"""
import argparse
import json
import os
import re
import time
from pathlib import Path

if __name__ == '__main__':
    os.environ['SERBIA_LAW_MCP'] = '1'
    os.environ['GLOBAL_LAW_JURISDICTIONS'] = 'serbia'

import mcp_server as mcp
import serbia_profile as profile
from serbia_citations import article_number


def citation_path(citation, files):
    # PIS numeric ref IDs and decisions cannot be mapped by guessing.
    got = re.fullmatch(r'sgrs/skupstina/zakon/(\d{4})/(\d+)/(\d+)::član ([^@]+)(?:@\d+)?', citation)
    if not got:
        return None
    year, issue, item, article = got.groups()
    folder = f'zakon/{year}/{issue}-{item}/'
    number = article_number(article)
    matches = [p for p in files if p.startswith(folder) and re.fullmatch(r'clan-[0-9a-z-]+\.md', p[len(folder):])
               and article_number(p[len(folder)+5:-3]) == number]
    return f'{profile.CORPUS}/{matches[0]}' if number and len(matches) == 1 else None


def result_paths(data, k):
    return list(dict.fromkeys(row['path'] for row in data.get('results', []) if row.get('path')))[:k]


def score(expected, ranked):
    if not expected:
        return None
    hits = set(expected).intersection(ranked)
    return {'recall': len(hits) / len(expected), 'hit': int(bool(hits)),
            'rr': next((1 / i for i, path in enumerate(ranked, 1) if path in hits), 0)}


def call(query, date, k, morphology):
    start = time.monotonic()
    response = mcp.handle({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {
        'name': 'search_law', 'arguments': {'query': query, 'date': date, 'jurisdiction': 'serbia',
                                            'max_results': min(200, k * 4), 'morphology': morphology}}})
    elapsed = round((time.monotonic() - start) * 1000)
    result = response.get('result', {})
    if result.get('isError') or 'structuredContent' not in result:
        return {}, elapsed, str(result.get('content', response.get('error', 'unknown error')))
    data = result['structuredContent']
    if data.get('left_out') or data.get('law_unread_for_time') or data.get('law_unread_count'):
        return data, elapsed, 'partial corpus search'
    return data, elapsed, None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('goldens', type=Path, help='External JSONL from RatkoNikolic/srb-legal-rag/goldens')
    parser.add_argument('--date', required=True, help='Fixed evaluation date for questions without as_of')
    parser.add_argument('--k', type=int, default=10, choices=range(1, 51), metavar='1..50')
    parser.add_argument('--limit', type=int, help='Run only the first N items for a smoke test')
    args = parser.parse_args()
    profile.install()
    sha = mcp.corpus_head(profile.CORPUS)
    if not sha:
        parser.error('Serbian corpus must be checked out, with its history')
    try:
        files = mcp.provisions(profile.CORPUS, sha)
    except (SystemExit, OSError):
        parser.error('Serbian corpus must be checked out, with its history')
    if not files:
        parser.error('Serbian corpus is empty or unavailable')
    items = [json.loads(line) for line in args.goldens.read_text(encoding='utf-8').splitlines() if line.strip()]
    rows = []
    for item in items[:args.limit]:
        query = item['query']['text']
        date = item['query'].get('as_of') or args.date
        citations = item.get('gold_citations', [])
        mapped = {c: citation_path(c, files) for c in citations}
        expected = set(filter(None, mapped.values()))
        row = {'id': item['item_id'], 'date': date, 'mapped': mapped, 'modes': {}}
        for mode in ('literal', 'morphology'):
            if not expected:
                continue
            # Full natural-language queries are used as-is. Morphology is only
            # applicable to short phrases; do not silently rewrite gold questions.
            data, ms, error = call(query, date, args.k, mode == 'morphology')
            ranked = result_paths(data, args.k)
            row['modes'][mode] = {'paths': ranked, 'ms': ms, 'error': error,
                                  'morphology_applied': data.get('morphology_applied', False),
                                  'score': None if error else score(expected, ranked)}
        rows.append(row)
    summary = {}
    for mode in ('literal', 'morphology'):
        runs = [r['modes'][mode] for r in rows if mode in r['modes']]
        valid = [r for r in runs if r['score'] is not None]
        summary[mode] = {'scored': len(valid), 'errors': len(runs) - len(valid),
                         'applied': sum(r['morphology_applied'] for r in runs),
                         **{key: sum(r['score'][key] for r in valid) / len(valid) if valid else None
                            for key in ('recall', 'hit', 'rr')},
                         'mean_ms': sum(r['ms'] for r in valid) / len(valid) if valid else None}
    print(json.dumps({'corpus_pin': sha, 'date': args.date, 'k': args.k, 'items': len(rows),
                      'mapped_citations': sum(bool(p) for r in rows for p in r['mapped'].values()),
                      'total_citations': sum(len(r['mapped']) for r in rows),
                      'summary': summary, 'rows': rows}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
