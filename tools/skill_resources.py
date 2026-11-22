"""Expose a language plugin's bundled SKILL.md files as ordinary MCP resources."""
from pathlib import Path


def load(root: Path, language: str) -> dict:
    skills = {}
    for entry in sorted((root / language / 'skills').glob('*/SKILL.md')):
        uri = f'skill://{language}/{entry.parent.name}/SKILL.md'
        skills[uri] = entry.read_text(encoding='utf-8')
    return skills


def describe(skills: dict) -> list:
    return [{'uri': uri, 'name': uri.split('/')[-2], 'mimeType': 'text/markdown'}
            for uri in skills]
