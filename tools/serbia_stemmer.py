"""Small, conservative Serbian inflection expander (stdlib only).

This is not a dictionary lemmatizer. It generates bounded suffix families for
lexical phrase search; it never changes a citation or the returned legal text.
"""
import re

# Longer, more specific families first; most require a four-letter root.
FAMILIES = (
    ('ација', 'ације', 'ацију', 'ацијом', 'ацијама', 'ацији'),
    ('ање', 'ања', 'ању', 'ањем', 'ањима'),
    ('ење', 'ења', 'ењу', 'ењем', 'ењима'),
    ('ског', 'ском', 'ским', 'ских', 'ски', 'ска', 'ско', 'ске', 'ску'),
    ('ног', 'ном', 'ним', 'них', 'ни', 'на', 'но', 'не', 'ну'),
    ('ама', 'има', 'ом', 'ем', 'а', 'е', 'и', 'у', 'о'),
)
LETTERS = 'абвгдђежзијклљмнњопрстћуфхцчџш'
WORD = re.compile('[' + LETTERS + ']+')


def stem(word):
    """Return a possible root and finite suffix family, not a proven lemma."""
    for index, family in enumerate(FAMILIES):
        for ending in sorted(family, key=len, reverse=True):
            if word.endswith(ending) and len(word) - len(ending) >= (3 if index == 3 else 4):
                return word[:-len(ending)], family
    if len(word) >= 5 and word[-1] not in 'аеиоу':
        return word, FAMILIES[-1]
    return word, ()


def phrase_pattern(query, transliterate, plain_pattern):
    """Generate a bounded POSIX ERE, or None for unsupported/non-word input."""
    if not isinstance(query, str):
        return None
    original = query.strip().lower().split()
    if not 1 <= len(original) <= 3:
        return None
    parts, expanded = [], False
    for token in original:
        word = transliterate(token) or token
        if not WORD.fullmatch(word):
            return None
        root, endings = stem(word)
        expanded |= bool(endings)
        head = root
        # Preserve upstream's ambiguity handling for ASCII input, without
        # importing the MCP engine or duplicating its transliteration table.
        if token.isascii():
            # Expand the original stem by using its ASCII prefix, when the
            # Cyrillic root can be located without splitting a digraph.
            prefix = next((token[:i] for i in range(len(token), 0, -1)
                           if transliterate(token[:i]) == root), None)
            if prefix:
                head = plain_pattern(prefix) or root
        part = head + '(' + '|'.join(endings) + ')?' if endings else head
        parts.append(part)
    if not expanded:
        return None
    pattern = '(^|[^[:alnum:]_])' + '[[:space:]]+'.join(parts) + '($|[^[:alnum:]_])'
    return pattern if len(pattern) <= 200 else None
