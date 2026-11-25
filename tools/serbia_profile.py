"""Serbian MCP interface; keep upstream's protocol, history and search engine."""
from copy import deepcopy
from functools import lru_cache
import logging
import re
import subprocess
import sqlite3

import mcp_server as upstream
import serbia_refs
import serbia_stemmer
import serbia_fts
from serbia_citations import ALIASES, GAZETTE, article_number, gazettes, normalize, parse, title_forms

CORPUS = serbia_refs.CORPUS
INSTRUCTIONS = (
    'MCP za propise Republike Srbije. Svi alati pretražuju samo srpski korpus. '
    'Upiti mogu biti na ćirilici, latinici ili bez dijakritika. Za konkretan član koristi get_provision '
    '(npr. čl. 21 st. 1 ZKP); za više citata resolve_citations; za tematsku pretragu search_law. '
    'Navedi datum primene propisa (YYYY-MM-DD), ne datum Git commita. Citiraj naziv propisa, član, '
    'provereni stav/tačku i službene izvore: prvenstveno cite.official_url, zatim source_links/sources iz rezultata pretrage. '
    'Navedi šta službeni link prikazuje: Consolidated je verzija teksta, Source je izvor evidentirane izmene i ne mora prikazivati važeći tekst. '
    'Uz službeni izvor izaberi najrelevantniji GitHub link: file_url za citiranje celog teksta na datum, '
    'file_diff_url za konkretnu izmenu člana (pre/posle), commit_url za akt o izmeni, njegove datume ili trailere. '
    'Ne moraš navoditi sva tri; koristi samo vraćene linkove i po potrebi dodaj drugi za kontekst. '
    'Ako službeni izvor nedostaje, reci to; ne izmišljaj linkove. Broj glasnika sam po sebi ne određuje '
    'verziju člana na datum. Ne tvrdi da propis važi van pokrivenosti korpusa; proveri caveats i freshness. '
    'serbia_metadata u pretrazi je pomoćni katalog: publication_key/issue/item iz putanje nisu potvrda službenog glasnika, '
    'a heading_context nije nužno naslov člana. Za citiranje koristi proverene izvore. '
    'Korpus nije potpuna baza sudske prakse. Odgovori na pravna pitanja moraju razlikovati tekst propisa od tumačenja.'
)
HIDDEN = {'world_on_date', 'check_precedent'}
LABELS = {
    'list_jurisdictions': ('Pokrivenost propisa Srbije', 'Proveri dostupne propise, vremenski opseg i ograničenja korpusa Srbije.'),
    'find_provision': ('Pronađi propis ili član', 'Pronađi putanju po nazivu, skraćenici (ZKP, KZ, ZOBS, ZPP), broju člana ili naslovu. Za tekst na određeni datum koristi get_provision.'),
    'read_law': ('Pročitaj propis', 'Tekst člana po putanji na datum primene, izvori, prethodna i naredna izmena. Može više putanja ili ceo propis.'),
    'who_wrote': ('Poreklo teksta člana', 'Koja izmena propisa je unela pojedine reči ili redove člana na datum.'),
    'compare_dates': ('Uporedi verzije', 'Uporedi tekst člana na dva datuma i izmene između njih.'),
    'provision_history': ('Istorija člana', 'Sve evidentirane izmene člana, datumi objave i stupanja na snagu.'),
    'laws_between': ('Propisi u periodu', 'Izmene propisa koje su stupile na snagu u datom periodu, uključujući oba datuma.'),
    'search_law': ('Pretraži tekst propisa', 'Pretraži tekst propisa Srbije na datum, npr. godišnji odmor, naknada štete. Vraća službene izvore verzije, kada postoje, i GitHub permalink. Podržava oba pisma. Za različite padeže kratke fraze koristi morphology=true.'),
    'changes_between': ('Izmene između datuma', 'Pronađi odredbe čiji se tekst razlikuje na dva datuma.'),
    'list_provisions': ('Pregled članova propisa', 'Prikaži članove ili pojedinačne propise u folderu na određeni datum.'),
    'search_changes': ('Pretraži izmene i glasnik', 'Pretraži evidenciju izmena, naziv propisa ili broj glasnika, npr. Sl. glasnik RS, br. 35/2019.'),
    'resolve_citations': ('Razreši pravne citate', 'Prepoznaj srpske citate iz teksta, npr. čl. 21 st. 1 ZKP; КЗ члан 246; Сл. гласник РС бр. 35/2019. Nerazrešeni i višeznačni citati se označavaju.'),
    'what_else_changes': ('Povezane odredbe', 'Pronađi evidentirane odredbe koje upućuju na član ili koriste pojam koji on definiše.'),
    'phrase_history': ('Istorija izraza', 'Kada se izraz pojavio u tekstu propisa i kada je izmenjen ili uklonjen.'),
    'applies_to_case': ('Vremenska primena', 'Proveri evidentirane prelazne odredbe i primenu na postupak započet određenog dana. Ne predstavlja sudsku praksu.'),
    'law_details': ('Detalji izmene propisa', 'Originalni zapis izmene, datumi, izvori, odredbe i razlike u tekstu. Koristi oznaku izmene ili commit iz istorije.'),
    'get_provision': ('Pronađi i pročitaj član', 'U jednom pozivu pronađi član srpskog propisa i pročitaj verziju na datum, npr. čl. 21 st. 1 ZKP. Stav i tačka se evidentiraju kao traženi, bez nagađanja granica pasusa.'),
}
PARAMETERS = {
    'query': 'Upit na srpskom (ćirilica ili latinica).', 'jurisdiction': 'Opcioni uži opseg unutar Srbije (putanja propisa); podrazumevano cela Srbija.',
    'date': 'Datum primene YYYY-MM-DD; podrazumevano danas.', 'date_a': 'Prvi datum YYYY-MM-DD.', 'date_b': 'Drugi datum YYYY-MM-DD.',
    'start': 'Početak perioda YYYY-MM-DD.', 'end': 'Kraj perioda YYYY-MM-DD.',
    'path': 'Putanja člana ili foldera iz rezultata pretrage, unutar serbia/national/acts.',
    'paths': 'Putanje više članova (umesto path).', 'max_results': 'Najveći broj rezultata.', 'offset': 'Preskoči rezultate (next_offset iz prethodnog odgovora).',
    'max_chars': 'Najveći broj znakova teksta u odgovoru.', 'text': 'Tekst koji sadrži pravne citate.',
    'include_text': 'Vrati i tekst člana (podrazumevano true).', 'kind': 'Propisi: laws ili law; all je isto što i laws.',
    'law': 'Naziv propisa, npr. Zakon o radu, ZKP ili oznaka izmene iz istorije.', 'commit': 'Git hash izmene iz istorije propisa.',
}

_BASE_TOOLS = upstream.tool_list
_BASE = dict(upstream.HANDLERS)


@lru_cache(maxsize=2)
def title_index(sha):
    index = {}
    for folder, info in upstream.folder_titles(CORPUS, sha).items():
        title = info.get('title', '')
        for name in [title, *info.get('names', [])]:
            for form in title_forms(name):
                if form:
                    index.setdefault(form, {})[folder] = title
    return index


def catalog():
    sha = upstream.corpus_head(CORPUS)
    if not sha:
        raise upstream.UserError('Srpski korpus nije dostupan.')
    return sha, title_index(sha)


def normalized_name(name):
    key = normalize(name).strip(' .')
    return normalize(ALIASES[key]) if key in ALIASES else key


def lookup(ref, date, args, sha, index):
    article = article_number(ref.get('article', ''))
    if not article:
        raise upstream.UserError('Navedi broj člana (npr. 21 ili 21a).')
    title = ref.get('law')
    base = {'requested': {**ref, 'article': article}, 'date': date}
    if not title:
        return {**base, 'status': 'unresolved', 'summary': 'Nedostaje jednoznačan naziv propisa uz član.'}
    if title.startswith(CORPUS + '/'):
        if '..' in title.split('/') or '\n' in title or '\r' in title or title.endswith('.md'):
            raise upstream.UserError('Navedi folder propisa, ne putanju pojedinačnog fajla.')
        matches = {title[len(CORPUS)+1:].rstrip('/'): title}
    else:
        matches = index.get(normalized_name(title), {})
    scope = upstream.scope_arg(args)
    matches = {f: t for f, t in matches.items() if not scope or (CORPUS + '/' + f).startswith(scope.rstrip('/') + '/') or CORPUS + '/' + f == scope}
    if not matches:
        return {**base, 'status': 'unresolved', 'summary': 'Naziv propisa nije jednoznačno pronađen. Koristi find_provision ili navedi tačnu putanju foldera.'}
    if len(matches) > 12:
        return {**base, 'status': 'ambiguous', 'candidates': [{'path': f'{CORPUS}/{f}', 'title': t} for f, t in list(matches.items())[:12]], 'summary': 'Više propisa istog naziva; navedi tačnu putanju.'}
    # Search the historical snapshot too: an article removed from HEAD must not disappear from dated requests.
    historical = upstream.law.pinned(upstream.law.root_on(date, upstream.law.timeline()), CORPUS)
    paths = []
    for folder, name in matches.items():
        files = set(upstream.provisions(CORPUS, sha, folder))
        if historical and historical != sha:
            files.update(upstream.provisions(CORPUS, historical, folder))
        for file in sorted(files):
            unit = re.fullmatch(r'clan-(\d+(?:-?[a-z])?)\.md', file.rsplit('/', 1)[-1])
            if unit and article_number(unit[1]) == article:
                paths.append((f'{CORPUS}/{file}', name))
    if not paths:
        return {**base, 'status': 'unresolved', 'summary': 'Član nije pronađen kao zaseban fajl u dostupnim verzijama. Proveri ceo propis i pokrivenost korpusa.', 'candidates': [{'path': f'{CORPUS}/{f}', 'title': t} for f, t in matches.items()]}
    if len(paths) > 1:
        live = [(p, t) for p, t in paths if upstream.run_law(upstream.law.text_on, date, p) is not None]
        if len(live) == 1:
            paths = live
        else:
            return {**base, 'status': 'ambiguous', 'summary': 'Više mogućih članova; navedi tačnu putanju propisa.', 'candidates': [{'path': p, 'title': t} for p, t in live or paths]}
    path, name = paths[0]
    body, data = read_law({'path': path, 'date': date, **{k: args[k] for k in ('include_text', 'max_chars', 'offset') if k in args}})
    body, data = serbia_refs.enrich('read_law', body, data, upstream.corpus_head)
    status = 'in force' if data.get('in_force') is True else 'not in force' if data.get('in_force') is False else 'unknown'
    result = {**data, **base, 'law_title': name, 'status': status}
    if args.get('include_text') is not False:
        result['_body'] = body
    if 'paragraph' in ref or 'point' in ref:
        result['subdivision_verified'] = False
        result['subdivision_note'] = 'Vraćen je član, ne izdvojeni stav ili tačka. Proveri numeraciju u originalnom tekstu.'
    if ref.get('gazettes'):
        result['gazette_note'] = 'Traženi brojevi glasnika nisu potvrda verzije; verzija je određena datumom primene.'
    return result


def get_provision(args):
    date = upstream.date_arg(args.get('date'))
    sha, index = catalog()
    citation = args.get('citation')
    if citation is not None:
        if not isinstance(citation, str) or len(citation) > 2000 or any(k in args for k in ('law', 'article', 'paragraph', 'point')):
            raise upstream.UserError('Navedi jedan citat (do 2000 znakova) ili law i article, ne oba.')
        refs = list(parse(citation, index))
        if len(refs) != 1:
            raise upstream.UserError('Navedi tačno jedan član; za više citata koristi resolve_citations.')
        ref = {**refs[0], 'gazettes': gazettes(citation)}
    else:
        if not isinstance(args.get('law'), str) or not isinstance(args.get('article'), (str, int)) or isinstance(args.get('article'), bool):
            raise upstream.UserError('Navedi law i article ili citation.')
        ref = {k: args[k] for k in ('law', 'article', 'paragraph', 'point') if k in args}
        for k in ('paragraph', 'point'):
            if k in ref and (type(ref[k]) is not int or ref[k] < 1):
                raise upstream.UserError(f'{k} mora biti pozitivan ceo broj.')
    data = lookup(ref, date, args, sha, index)
    text = '\n'.join(str(v) for v in (data.pop('_body', data['summary']), data.get('subdivision_note'), data.get('gazette_note'), data.get('file_url'), data.get('commit_url'), data.get('file_diff_url'), (data.get('cite') or {}).get('official_url')) if v)
    return text, data


def resolve_citations(args):
    text = args.get('text')
    if not isinstance(text, str) or not text.strip() or len(text) > upstream.MAX_BRIEF:
        raise upstream.UserError(f'Navedi tekst do {upstream.MAX_BRIEF} znakova.')
    date = upstream.date_arg(args.get('date'))
    scope = upstream.scope_arg(args) or 'serbia'
    sha, index = catalog()
    refs = list(parse(text, index))
    issues = gazettes(text)
    limit = upstream.num(args, 'max_results', 10, 20)
    rows = [lookup(ref, date, {'include_text': False, 'jurisdiction': scope}, sha, index) for ref in refs[:limit]]
    records = []
    for issue in issues[:min(limit, 5)]:
        _, data = _BASE['search_changes']({'query': f'Службени гласник РС {issue}', 'jurisdiction': scope, 'max_results': 10})
        _, data = serbia_refs.enrich('search_changes', '', data, upstream.corpus_head)
        records.append({'issue': issue, 'changes': data.get('changes', []), 'page': data.get('page'), 'summary': data.get('summary')})
    summary = f'Provereno {len(rows)} od {len(refs)} citata članova i {len(records)} od {len(issues)} brojeva glasnika na datum {date} (glasnik je evidencija objave, ne izbor verzije).'
    return summary + '\n' + '\n'.join(f"{r['requested']}: {r['status']} — {r.get('path', r['summary'])}" for r in rows), {
        'summary': summary, 'date': date, 'citations': rows, 'gazettes': records,
        'truncated': len(rows) < len(refs) or len(records) < len(issues),
        'note': 'Neprepoznati oblici, rasponi i višestruki stavovi mogu zahtevati ručnu proveru. Stav i tačka nisu izdvojeni iz teksta.'}


def find_provision(args):
    query = args.get('query')
    if isinstance(query, str):
        key = normalize(query).strip(' .')
        if key in ALIASES:
            args = {**args, 'query': ALIASES[key]}
        elif re.search(r'\d', query):
            _, index = catalog()
            refs = list(parse(query, index))
            if len(refs) == 1 and refs[0].get('law'):
                ref = refs[0]
                titles = set(index.get(normalized_name(ref['law']), {}).values())
                if len(titles) == 1:
                    title, = titles
                    # Upstream finds the article or returns the act when it is held as one text.
                    args = {**args, 'query': f"{title} члан {ref['article']}"}
    return _BASE['find_provision'](args)


def search_changes(args):
    query = args.get('query')
    if isinstance(query, str) and GAZETTE.fullmatch(normalize(query).strip('„“”". ')):
        args = {**args, 'query': f'Службени гласник РС {gazettes(query)[0]}'}
    return _BASE['search_changes'](args)


def read_law(args):
    text, data = _BASE['read_law'](args)
    path, date = data.get('path', ''), data.get('date', '')
    match = re.fullmatch(re.escape(CORPUS) + r'/zakon/(\d{4})/([a-z]*\d+-\d+)/clan-\d+(?:-?[a-z])?\.md', path)
    generic = '; it may well have been in force then.'
    why = data.get('why', '')
    if (match and data.get('in_record') is False and data.get('in_force') is None
            and date[:4] < match[1] and generic in why):
        note = (f" The act's folder identifies its first publication year as {match[1]} "
                f"and its publication identifier as {match[2]}; "
                "this is not an enactment or commencement date and does not rule out retroactive effect. "
                "This lookup does not verify a predecessor or an equivalent provision. Check the official publication "
                "and search earlier acts by title and subject; article numbers and wording can differ.")
        revised = why.replace(generic, '.' + note)
        text = text.replace(why, revised, 1)
        data = {**data, 'why': revised, 'summary': upstream.first_line(revised),
                'publication_year': int(match[1]), 'historical_coverage_note': note.strip()}
    return text, data


def _search_law(args):
    args = dict(args)
    enabled = args.pop('morphology', False)
    if type(enabled) is not bool:
        raise upstream.UserError('morphology mora biti true ili false.')
    # The upstream index hook serves whole-corpus, current, plain searches.
    # Preserve all original dated, scoped and regex search behavior.
    if not args.get('regex') and not args.get('case_sensitive') and upstream.date_arg(args.get('date')) == upstream.law.day('today'):
        scope = upstream.scope_arg(args)
        query = upstream.text_arg(args, 'query')
        if upstream.scoped(CORPUS, scope) == '' and (not enabled or 1 <= len(query.split()) <= 3):
            try:
                prepared = serbia_fts.prepare(query, enabled)
            except (OSError, ValueError, RuntimeError, subprocess.SubprocessError, sqlite3.Error):
                logging.getLogger(__name__).warning('Serbian FTS unavailable; using Git search', exc_info=True)
                prepared = None
            if prepared is not None:
                text, data = upstream.t_search_law({**args, 'query': prepared})
                try:
                    rows = data.get('results', [])
                    metadata = upstream.search_index.metadata(prepared, list(dict.fromkeys(
                        row['path'][len(CORPUS) + 1:] for row in rows if row['path'].startswith(CORPUS + '/'))))
                    for row in rows:
                        if info := metadata.get(row['path'][len(CORPUS) + 1:]):
                            row['serbia_metadata'] = info
                except sqlite3.Error:
                    logging.getLogger(__name__).warning('Serbian FTS metadata unavailable', exc_info=True)
                data = {**data, 'search_backend': 'sqlite_fts5', 'morphology_applied': enabled}
                if enabled:
                    note = 'Približna pretraga padežnih oblika; proveri relevantnost izvornog teksta.'
                    return note + '\n' + text, {**data, 'morphology_note': note, 'morphology_query': query}
                return text, data
    if not enabled:
        return _BASE['search_law'](args)
    if args.get('regex') or args.get('case_sensitive'):
        raise upstream.UserError('morphology se ne kombinuje sa regex ili case_sensitive.')
    args.setdefault('jurisdiction', 'serbia')
    scope = upstream.scope_arg(args)
    if scope != 'serbia' and not scope.startswith('serbia/'):
        raise upstream.UserError('Morfološka pretraga dostupna je samo za Srbiju.')
    pattern = serbia_stemmer.phrase_pattern(args.get('query'), upstream.serbian_cyrillic,
                                          upstream.serbian_plain_pattern)
    if not pattern:
        text, data = _BASE['search_law'](args)
        note = 'Morfološko proširenje nije dostupno za ovaj izraz; korišćena je redovna pretraga.'
        return note + '\n' + text, {**data, 'morphology_applied': False, 'morphology_note': note}
    text, data = _BASE['search_law']({**args, 'query': pattern, 'regex': True})
    note = 'Približna pretraga padežnih oblika; proveri relevantnost izvornog teksta.'
    return note + '\n' + text, {**data, 'morphology_applied': True, 'morphology_query': args['query'], 'morphology_note': note}


def search_law(args):
    text, data = _search_law(args)
    date = data.get('date') or upstream.date_arg(args.get('date'))
    empty = data.get('page', {}).get('total') == 0 or ('page' not in data and data.get('results') == [])
    if date < upstream.law.day('today') and empty:
        note = ('Nema rezultata u dostupnom korpusu; ukinuti propisi i ranije verzije mogu nedostajati. '
                'To ne dokazuje da propis ili odgovarajuća odredba nisu postojali.')
        text += '\n' + note
        data = {**data, 'caveats': [*data.get('caveats', []), note]}
    return text, data


GET_PROPERTIES = {
    'citation': {'type': 'string', 'description': 'Jedan citat, npr. čl. 21 st. 1 ZKP ili КЗ члан 246.'},
    'law': {'type': 'string', 'description': 'Tačan naziv, skraćenica (ZKP, KZ, ZOBS, ZPP) ili folder propisa.'},
    'article': {'type': ['string', 'integer'], 'description': 'Broj člana, npr. 21 ili 21a.'},
    'paragraph': {'type': 'integer', 'minimum': 1, 'description': 'Traženi stav; vraća se ceo član.'},
    'point': {'type': 'integer', 'minimum': 1, 'description': 'Tražena tačka; vraća se ceo član.'},
    'date': upstream.DATE, 'include_text': {'type': 'boolean'}, 'jurisdiction': upstream.SCOPE, **upstream.PAGE,
}


def tool_list():
    tools = [deepcopy(t) for t in _BASE_TOOLS() if t['name'] not in HIDDEN]
    tools.append({'name': 'get_provision', 'inputSchema': {'type': 'object', 'properties': deepcopy(GET_PROPERTIES), 'additionalProperties': False}, 'annotations': dict(upstream.RO)})
    for tool in tools:
        name = tool['name']
        tool['title'], tool['description'] = LABELS[name]
        tool['annotations']['title'] = tool['title']
        props = tool['inputSchema']['properties']
        if name == 'search_law':
            props['morphology'] = {'type': 'boolean', 'default': False, 'description': 'Opciona približna pretraga padežnih oblika kratke fraze (1–3 reči); ne kombinuje se sa regex ili case_sensitive.'}
        if name == 'resolve_citations':
            props['jurisdiction'] = deepcopy(upstream.SCOPE)
            props['max_results']['description'] = 'Najviše 20 citata članova (podrazumevano 10) i do 5 brojeva glasnika.'
        if 'kind' in props:
            props['kind']['enum'] = ['laws', 'law', 'all']
        for key, schema in props.items():
            if key in PARAMETERS and not (name == 'get_provision' and key == 'law') and not (name == 'resolve_citations' and key == 'max_results'):
                schema['description'] = PARAMETERS[key]
    return tools


def install():
    """Install only in the Serbia entry points, never in upstream's global server."""
    upstream.INSTRUCTIONS = INSTRUCTIONS
    upstream.search_index = serbia_fts.Index()
    upstream.tool_list = tool_list
    upstream.PROMPTS = {
        'provision_on_a_date': ('Član na datum', 'Proveri tekst važeći na određeni datum.',
            [{'name': 'provision', 'description': 'Pravni citat, npr. čl. 21 ZKP', 'required': True},
             {'name': 'date', 'description': 'YYYY-MM-DD', 'required': True}],
            'Koristi get_provision za {provision} na datum {date} i prikaži izvore i ograničenja.'),
    }
    for name in HIDDEN:
        upstream.HANDLERS.pop(name, None)
    upstream.HANDLERS.update(get_provision=get_provision, resolve_citations=resolve_citations,
                             find_provision=find_provision, read_law=read_law,
                             search_changes=search_changes, search_law=search_law)
    if 'morphology' not in upstream.PROPERTIES['search_law']:
        upstream.PROPERTIES['search_law'].append('morphology')
    upstream.PROPERTIES['get_provision'] = list(GET_PROPERTIES)
    if 'jurisdiction' not in upstream.PROPERTIES['resolve_citations']:
        upstream.PROPERTIES['resolve_citations'].append('jurisdiction')


if __name__ == '__main__':
    install()
    upstream.main()
