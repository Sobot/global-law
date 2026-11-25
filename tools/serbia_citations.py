"""Conservative parsing of Serbian statutory references (no legal inference)."""
import re
import unicodedata


_CYR = dict(zip('абвгдђежзијклљмнњопрстћуфхцчџш',
                ('a','b','v','g','d','dj','e','z','z','i','j','k','l','lj','m','n','nj','o','p','r','s','t','c','u','f','h','c','c','dz','s')))


def normalize(text):
    text = unicodedata.normalize('NFKC', text).casefold().replace('đ', 'dj')
    text = ''.join(_CYR.get(c, c) for c in text)
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD', text)
                            if not unicodedata.combining(c)).split())


ALIASES = {
    'zkp': 'Zakonik o krivičnom postupku', 'kz': 'Krivični zakonik',
    'zobs': 'Zakon o bezbednosti saobraćaja na putevima',
    'zpp': 'Zakon o parničnom postupku', 'zoo': 'Zakon o obligacionim odnosima',
    'zup': 'Zakon o opštem upravnom postupku', 'zio': 'Zakon o izvršenju i obezbeđenju',
    'zus': 'Zakon o upravnim sporovima', 'ustav rs': 'Ustav Republike Srbije',
    'ustav': 'Ustav Republike Srbije',
}

ARTICLE = re.compile(r'\b(?:clan(?:a|u|om)?|cl)\.?\s*(\d{1,6}(?!\d)(?:\s*[-–]?\s*[a-z](?!\w))?)\.?')
UNIT = re.compile(r'\s*(?:,\s*)?(?P<kind>stav(?:a|u)?|st|tack(?:a|e|i|u)|tac|t)\.?\s*(?P<num>\d{1,6})(?!\d)\.?\)?')
GAZETTE = re.compile(r'\b(?:sluzbeni\s+glasnik|sl\.?\s*glasnik)\s+rs\s*[,„“”" ]*\s*(?:br(?:oj)?\.?\s*)?(\d{1,6})\s*/\s*(\d{4})\b')


def article_number(value):
    match = re.fullmatch(r'(\d{1,6})(?:\s*[-–]?\s*([a-z]))?\.?', normalize(str(value)))
    return str(int(match[1])) + (match[2] or '') if match else None


def title_forms(title):
    name = normalize(title).strip(' .')
    yield name
    for first, inflected in (('zakon ', 'zakona '), ('zakonik ', 'zakonika '),
                              ('ustav ', 'ustava '), ('pravilnik ', 'pravilnika '),
                              ('uredba ', 'uredbe '), ('odluka ', 'odluke ')):
        if name.startswith(first):
            yield inflected + name[len(first):]
    if name.endswith(' zakonik'):
        yield name + 'a'
        if name.startswith('krivicni '):
            yield 'krivicnog zakonika'


def gazettes(text):
    return list(dict.fromkeys(f'{int(m[1])}/{m[2]}' for m in GAZETTE.finditer(normalize(text))))


def parse(text, names):
    """Find article references with an adjacent exact law title/alias; retain unresolved ones."""
    plain = normalize(text)
    articles = list(ARTICLE.finditer(plain))
    # Only adjacent names count: never pick another act merely because it is mentioned elsewhere.
    names = set(names) | set(ALIASES)
    for i, match in enumerate(articles):
        end = match.end()
        row = {'article': article_number(match[1])}
        while unit := UNIT.match(plain, end):
            key = 'paragraph' if unit['kind'].startswith('st') else 'point'
            if key in row:
                break
            row[key] = int(unit['num'])
            end = unit.end()
        left = plain[articles[i-1].end() if i else 0:match.start()].rstrip(' ,:(')
        right = plain[end:articles[i+1].start() if i+1 < len(articles) else len(plain)].lstrip(' ,:(')
        # Try prefixes/suffixes of consecutive words, longest first. A name may contain punctuation.
        before = left.split()[-32:]
        after = right.split()[:32]
        lhs = next((' '.join(before[-n:]) for n in range(len(before), 0, -1)
                    if ' '.join(before[-n:]) in names), None)
        rhs = next((' '.join(after[:n]).rstrip('.,;:)') for n in range(len(after), 0, -1)
                    if ' '.join(after[:n]).rstrip('.,;:)') in names), None)
        # A conflicting name is ambiguous rather than silently attributed to either act.
        if lhs and rhs and lhs != rhs:
            row['law_candidates'] = [lhs, rhs]
        elif rhs or lhs:
            row['law'] = rhs or lhs
        row['citation'] = plain[match.start():end].strip()
        yield row
