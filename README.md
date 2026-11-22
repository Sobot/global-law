# Zakon — MCP za propise Republike Srbije

Pitajte asistenta kako glasi član zakona, koji je tekst važio na određeni datum ili šta se promenilo između dve verzije. Odgovor možete proveriti preko linka na tekst člana u odgovarajućoj verziji ili na izmenu koja ga je uvela.

## Povezivanje

U klijentu koji podržava udaljene MCP servere dodajte konektor sa sledećim podacima.

| Polje | Vrednost |
| --- | --- |
| Naziv | `zakon` |
| Opis | Pretraga važećih i istorijskih propisa Republike Srbije sa referencama na članove, verzije i izmene. |
| Test MCP URL | `https://d38cy0uwrxlk77.cloudfront.net/mcp` |
| Transport | Streamable HTTP |

## Šta možete da pitate

> @zakon Kako je glasio cl. 21 st. 1 ZKP 29. maja 2019? Daj mi link na izvor.

Konektor prepoznaje oznaku člana i kada je upišete bez kvačica. U ovom primeru pronalazi Zakonik o krivičnom postupku i vraća [član 21 „Sastav sudskih veća“ u verziji za 29. maj 2019.](https://github.com/lexifina/serbia-law/blob/09019e8e6a8d73d50b8dfe9a647642cfe35761f7/zakon/2011/72-3/clan-021.md). Link vodi na ceo član. Prilikom citiranja pojedinačnog stava ili tačke proverite njihove granice u tekstu.

> @zakon Упореди члан 21 ЗКП како је гласио 28. и 29. маја 2019. Прикажи само шта се променило и дај линкове на обе верзије.

> @zakon Koja izmena ZKP-a je objavljena u „Sl. glasniku RS“, br. 35/2019? Daj mi link na izmenu.

Treći primer koristi broj glasila da pronađe [komit sa izmenom](https://github.com/lexifina/serbia-law/commit/09019e8e6a8d73d50b8dfe9a647642cfe35761f7). Za pitanje o važenju navedite i datum koji vas zanima. Ako za taj period nedostaje tekst, odgovor treba da navede granicu dostupne istorije.

Za tematsku pretragu različitih padežnih oblika može se uključiti `search_law(query="naknada štete", morphology=true)`. To je opciona, približna pretraga kratkih fraza (1–3 reči), bez spoljnog API-ja. Redovna pretraga, citati i istorija ostaju nepromenjeni. Rezultati sadrže originalni tekst, ne generisane oblike.

### Lokalni indeks pretrage

Pretraga celog srpskog korpusa na današnji datum koristi SQLite FTS5 kada je indeks spreman. Ćirilica, latinica i latinica bez dijakritika imaju zajedničku normalizaciju; `morphology=true` koristi zasebnu kolonu korena reči. Istorijski, regex, case-sensitive i uži upiti i dalje koriste Git. FTS čuva indeks i lokacije redova, bez dupliranja originalnog teksta; relevantni originalni redovi čitaju se iz Git blobova.

`python tools/serbia_fts.py` gradi indeks u `.git/global-law-cache/serbia-fts/`. Ključ je Git tree teksta koji danas važi i hash implementacije normalizacije i indeksiranja, ne SHA aplikacije. CI ga kešira, a test server ga ponovo koristi iz trajnog lokalnog keša. Novi indeks nastaje samo ako se promeni efektivni sadržaj ili implementacija; binarna baza se ne komituje. Dok se prvi indeks gradi, server ostaje dostupan preko Git pretrage.

SQLite dodatno čuva kompaktan katalog akata: vrstu i putanju akta, naziv iz postojećeg Global Law kataloga, poznate srpske skraćenice, identifikator objave iz putanje (godina, broj i stavka kada su jednoznačno kodirani), broj člana, zaglavlje i kontekst zaglavlja. Ovi podaci se vraćaju kao `serbia_metadata` u rezultatima FTS pretrage. Identifikator putanje nije potvrda službenog glasnika niti datuma stupanja na snagu; za to se koristi upstream istorija. Otisak naziva iz kataloga takođe ulazi u ključ indeksa. Ne kopiraju se Git istorija, datumi važenja, izmene, niti službeni izvori, jer ih Global Law već indeksira.

`search_law` (FTS i istorijska Git pretraga) uz `file_url` vraća `version_commit`, `last_change` (uključujući datum stupanja na snagu i objave) i `source_links`/`sources` iz odgovarajućeg commita, kada su dostupni. `Source` označava izvor izmene, a `Consolidated` verziju teksta. Poruke jedinstvenih commitova sa strane rezultata čitaju se grupno i keširaju po SHA; FTS indeks ostaje nepromenjen.

Ručna obnova: **Actions → Serbia MCP CI and deployment → Run workflow → force_rebuild_index**. Na `main` obnavlja i indeks na test serveru, čak i ako je isti commit već deployovan. Lokalno: `python tools/serbia_fts.py --force`. Nova baza se objavljuje atomarno tek nakon izgradnje; neuspeh ostavlja prethodnu.

## Benchmark pretrage

Lokalni `tools/serbia_benchmark.py` meri Recall@K, Hit@K, MRR@K i trajanje pretrage na istom datumu i Git pinu. Ne ocenjuje pravno tumačenje. Koristi postojeća [pitanja srb-legal-rag](https://github.com/RatkoNikolic/srb-legal-rag/tree/bd839dc35da24250268e9c95b93d5834ad8ba828/goldens) autora Ratka Nikolića (CC BY 4.0); originalni skup nije kopiran u ovaj repozitorijum.

```sh
git clone https://github.com/RatkoNikolic/srb-legal-rag.git ../srb-legal-rag
git -C ../srb-legal-rag checkout bd839dc35da24250268e9c95b93d5834ad8ba828
python tools/serbia_benchmark.py ../srb-legal-rag/goldens/golden-situational-60.jsonl --date 2026-11-22 --k 10
python tools/serbia_benchmark.py tests/serbia/morphology-benchmark.jsonl --date 2019-05-29 --k 10
```

Potreban je postojeći checkout srpskog korpusa sa istorijom. Neusaglašeni identifikatori, nedostajući članci i greške prijavljuju se odvojeno. Rezultati nisu direktno uporedivi sa RAG benchmarkom tačnosti odgovora. Duga situaciona pitanja se ne prepravljaju u ključne reči; morfološko proširenje se posebno proverava kratkim frazama u jediničnim testovima.

## Uputstva za asistente

Paket sadrži [tri uputstva (skills)](plugins/sr/skills/) za citiranje odredbe, utvrđivanje teksta koji je važio na određeni datum i poređenje verzija. Server ih izlaže kao MCP resurse koje klijent može da pročita.

## Poreklo projekta i licenca

Ovaj server je srpska adaptacija projekta [Global Law](https://github.com/lexifina/global-law). Tekstovi propisa i istorija izmena dolaze iz [korpusa za Srbiju](https://github.com/lexifina/serbia-law). Dokumentacija izvornog projekta opisuje [zajedničke alate i komande](FEATURES.md) i [globalni MCP interfejs](MCP.md).

Ovaj repozitorijum je objavljen pod [CC0](LICENSE.md). Za tekstove propisa važe uslovi navedeni u repozitorijumu korpusa.
