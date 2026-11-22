"""Report Serbian translations in docs/sr-Cyrl whose English original changed after they were translated.

Each translation starts with `<!-- upstream: FILE.md @ <commit> -->`, naming the original and the commit it was
translated from. A translation is stale when the original differs between that commit and HEAD; the diff shows what to
carry over. Exit status is 1 when any translation is stale or its header is missing or unreadable.
    python tools/check_translations.py [--diff]
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs' / 'sr-Cyrl'
HEADER = re.compile(r'<!-- upstream: (\S+) @ ([0-9a-f]{7,40}) -->')


def git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True)


def check(root: Path = ROOT) -> list[tuple[str, str, str, str]]:
    """(translation, original, commit, problem) for every translation that needs attention."""
    problems = []
    for doc in sorted((root / DOCS.relative_to(ROOT)).glob('*.md')):
        first = doc.read_text(encoding='utf-8').split('\n', 1)[0]
        match = HEADER.fullmatch(first.strip())
        if not match:
            continue  # documents written for this edition, with no English original
        original, commit = match.groups()
        name = doc.relative_to(root).as_posix()
        if git(root, 'cat-file', '-e', f'{commit}^{{commit}}').returncode:
            problems.append((name, original, commit, 'commit not in this clone (fetch full history)'))
        elif git(root, 'diff', '--quiet', commit, 'HEAD', '--', original).returncode:
            problems.append((name, original, commit, 'original changed since translation'))
    return problems


def main(argv: list[str]) -> int:
    problems = check()
    for name, original, commit, problem in problems:
        print(f'{name}: {problem} ({original} @ {commit[:12]})')
        if '--diff' in argv and problem.startswith('original changed'):
            print(git(ROOT, '--no-pager', 'diff', '--stat', commit, 'HEAD', '--', original).stdout)
    if not problems:
        print(f'All translations in {DOCS.relative_to(ROOT).as_posix()} are current.')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
