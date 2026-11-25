import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from serbia_citations import article_number, gazettes, normalize, parse, title_forms


class SerbiaCitationParserTest(unittest.TestCase):
    def test_scripts_and_units(self):
        for citation in ('чл. 21. ст. 1. тач. 2. ЗКП', 'cl. 21 st. 1 tac. 2 ZKP',
                         'član 21 stav 1 tačka 2 ZKP'):
            row, = parse(citation, {})
            self.assertEqual((row['law'], row['article'], row['paragraph'], row['point']), ('zkp', '21', 1, 2))

    def test_title_and_suffix(self):
        names = set(title_forms('Zakon o radu'))
        row, = parse('člana 12a Zakona o radu', names)
        self.assertEqual((row['law'], row['article']), ('zakona o radu', '12a'))
        row, = parse('КЗ члан 246а', {})
        self.assertEqual((row['law'], row['article']), ('kz', '246a'))
        self.assertEqual(article_number('021-a'), '21a')

    def test_multiple_and_ambiguous(self):
        rows = list(parse('ZOBS član 330; KZ čl. 246', {}))
        self.assertEqual([r['law'] for r in rows], ['zobs', 'kz'])
        row, = parse('ZKP čl. 21 KZ', {})
        self.assertNotIn('law', row)
        self.assertEqual(row['law_candidates'], ['zkp', 'kz'])
        row, = parse('član 12 nepoznatog zakona', {})
        self.assertNotIn('law', row)

    def test_gazette(self):
        self.assertEqual(gazettes('„Службени гласник РС”, бр. 35/2019; Sl. glasnik RS 35/2019'), ['35/2019'])
        self.assertEqual(normalize('Љ Њ Ђ Џ'), 'lj nj dj dz')


if __name__ == '__main__':
    unittest.main()
