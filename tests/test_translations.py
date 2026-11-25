import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import check_translations


class Translations(unittest.TestCase):
    def test_reports_a_translation_whose_original_changed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            git = lambda *a: subprocess.run(['git', '-C', folder, '-c', 'user.name=T', '-c', 'user.email=t@e', *a],  # noqa: E731
                                            check=True, capture_output=True, text=True).stdout.strip()
            git('init', '-q')
            (root / 'docs/sr-Cyrl').mkdir(parents=True)
            for name in ('A.md', 'B.md'):
                (root / name).write_text('one\n', encoding='utf-8')
            git('add', '.'), git('commit', '-qm', 'originals')
            base = git('rev-parse', 'HEAD')
            for name in ('A.md', 'B.md'):
                (root / 'docs/sr-Cyrl' / name).write_text(f'<!-- upstream: {name} @ {base} -->\n# Превод\n', encoding='utf-8')
            (root / 'docs/sr-Cyrl/SRBIJA.md').write_text('# Само српско\n', encoding='utf-8')
            (root / 'B.md').write_text('two\n', encoding='utf-8')
            git('add', '.'), git('commit', '-qm', 'B changes')

            problems = check_translations.check(root)
            self.assertEqual([(p[0], p[3]) for p in problems],
                             [('docs/sr-Cyrl/B.md', 'original changed since translation')])

    def test_repository_translations_name_known_commits(self):
        for name, original, commit, problem in check_translations.check():
            self.assertNotIn('not in this clone', problem, name)  # CI fetches full history


if __name__ == '__main__':
    unittest.main()
