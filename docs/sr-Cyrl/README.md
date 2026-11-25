<!-- upstream: README.md @ 8a81ec4d2256a865f829e97102652a8b52aa0641 -->
# Git за светско право

> Превод оригинала [README.md](../../README.md) на српски. Измене специфичне за српско издање означене су као „Напомена за српско издање“ и описане у [SRBIJA.md](SRBIJA.md).

**Право целог света у једној git историји. Свака реч праћена до закона који ју је написао, за било коју земљу и било
који датум.**

Проширење истог пројекта за US Code, [бр. 1 на Hacker News-у (28/10/26)](https://news.ycombinator.com/item?id=50268380).
Семантичко право, по којем се може претраживати, у глобалним размерама.

https://github.com/user-attachments/assets/f24f3411-24d9-416a-8c45-9cebc817c64e

**Слободно за коришћење: [CC0](../../LICENSE.md).** Направите fork, градите на њему, уградите га у производ: није
потребна ни дозвола ни навођење. Текст закона налази се у репозиторијуму сваке земље, под сопственим условима тог
репозиторијума.

Свака целина права је засебан репозиторијум: право неке земље (`lexifina/germany-law`), државе (федералне јединице) или
града (`lexifina/germany-brandenburg-law`), или одлуке неког суда (`lexifina/germany-bgh-caselaw`). У датираној
историји сваки комит је један закон који ступа на снагу, а аутор комита је тај закон; у судској пракси, једна одлука на
дан када је донета. Тамо где издавач чува само данашњи текст, или сваки закон само у облику у којем је први пут
донет, корпус то наводи (`history` у `manifest.json`). Овај репозиторијум их све садржи као подмодуле, распоређене по
јурисдикцијама, и сваки помера напред до његовог најновијег комита. Алати читају `In-force` датум сваког комита, па дају
право било које земље на било који датум који њена евиденција покрива.

За Србију, стање одредбе пре прве доступне верзије може бити непознато. Када `read_law` из путање акта прикаже
каснију годину првог објављивања, та година није датум доношења или ступања на снагу и не искључује повратно дејство.
Претходни прописи и одговарајуће одредбе нису аутоматски повезани; укинути прописи и раније верзије могу недостајати.
Празна историјска претрага не доказује да нису постојали. Проверите службене објаве и претражите раније прописе по
називу и теми, јер се бројеви чланова и формулације могу разликовати.

> **Напомена за српско издање:** овај fork (Sobot/global-law) покрива само Србију: преузет је само `serbia/national/acts` (подмодул lexifina/serbia-law), а подмодули осталих земаља су уклоњени. Српски тест сервер налази се на `https://d38cy0uwrxlk77.cloudfront.net/mcp`. Детаљи су у [SRBIJA.md](SRBIJA.md).

```
global-law/
├── manifest.json                       every corpus: path, repository, history, coverage and dates
├── jurisdiction.json                   the world, and the jurisdictions in it
├── germany/bund/acts/                  a country's law (submodule: lexifina/germany-law)
├── germany/brandenburg/acts/           a state's
├── argentina/buenos-aires/salto/acts/  a city's
├── germany/bgh/caselaw/                a court's decisions
├── tools/                              law.py, the MCP server, countries.py
└── …
```

(`manifest.json`: сваки корпус – путања, репозиторијум, историја, покривеност и датуми; `jurisdiction.json`: свет и
јурисдикције у њему; `germany/bund/acts/`: право једне земље (подмодул lexifina/germany-law); `germany/brandenburg/acts/`:
право једне државе; `argentina/buenos-aires/salto/acts/`: право једног града; `germany/bgh/caselaw/`: одлуке једног
суда; `tools/`: law.py, MCP сервер, countries.py.)

## Питања као команде

| Питање | Команда |
| --- | --- |
| Свака измена 11 U.S.C. §1182, са законом који је унео сваку од њих | `python3 tools/law.py log united-states/federal/usc/title-11/1182.md` |
| Који закон је написао сваки њен ред данас? | `python3 tools/law.py blame 2026-01-01 united-states/federal/usc/title-11/1182.md` |
| §1182 како је био на снази 1. маја 2022. | `python3 tools/law.py show 2022-05-01 united-states/federal/usc/title-11/1182.md` |
| Шта се променило између два датума | `python3 tools/law.py diff 2022-05-01 2022-07-01 united-states/federal/usc/title-11/1182.md` |
| Последњи закон на снази у свакој земљи на одређени дан | `python3 tools/law.py world 1990-10-03` |
| Члан 21 закона из „Службеног гласника РС“ бр. 72/2011 како је гласио 29. маја 2019. | `python3 tools/law.py show 2019-05-29 serbia/national/acts/zakon/2011/72-3/clan-021.md` |

> **Напомена за српско издање:** последњи ред табеле је српски пример додат у овом fork-у; амерички примери раде тек када додате тај корпус (`python3 tools/countries.py add united-states/federal/usc`). Српски тест сервер је на `https://d38cy0uwrxlk77.cloudfront.net/mcp` (Streamable HTTP, конектор `zakon`); јавни сервер `https://global-law.lexifina.com/mcp` и везе испод припадају upstream-у и покривају цео свет. У овом fork-у `.vscode/mcp.json` повезује VS Code са удаљеним тест сервером `zakon`, а не са локалним сервером.

Сваки корпус је и обичан git репозиторијум (`git -C united-states/federal/usc log -- title-11/1182.md`); алати ређају
верзије по њиховом `In-force` датуму, што је важно тамо где евиденција није комитована тим редоследом.

**Ван git-а**, ову евиденцију такође јавно и бесплатно хостујемо:

- **[Питајте Claude о праву](https://global-law.lexifina.com/v1/try_claude)**: отвара Claude са већ припремљеним првим
  питањем.
- **[Питајте ChatGPT](https://global-law.lexifina.com/v1/try_chatgpt)**: исто питање у ChatGPT-у.
- **[Претражите право на нашем сајту](https://lexifina.com/law?country=united-states&q=small+business+debtor)**: претрага
  права САД за „small business debtor“, са текстом и верзијама сваке одредбе, без налога; тамо можете изабрати било
  коју земљу.
- **[REST API за програмере](https://global-law.lexifina.com/v1/search_law?query=small+business+debtor&jurisdiction=united-states)**:
  иста претрага као JSON, без кључа. Погледајте [документацију овде](https://lexifina.com/api/global-law).

Оба асистента читају евиденцију преко бесплатног конектора Global law (MCP, `https://global-law.lexifina.com/mcp`);
први пут вам ћаскање даје везу којом га додајете. Питајте на било ком језику; за једну земљу, додајте `?country=romania`
било којој од те две везе.

**Лако га хостујте сами.** Потребни су само git и Python, а алати раде на вашем рачунару:

```sh
git clone --depth 1 https://github.com/lexifina/global-law && cd global-law
python3 tools/countries.py add united-states/federal/usc
python3 tools/law.py show 2022-05-01 united-states/federal/usc/title-11/1182.md
```

Када се отвори у Claude Code-у, Cursor-у, VS Code-у или Codex-у, клон покреће и локални MCP сервер са истим алатима
([MCP.md](MCP.md)). [FEATURES.md](FEATURES.md) наводи сваку команду, а [FAQ.md](FAQ.md) како клонирати.

## Судска пракса

[Судске одлуке](FAQ.md#да-ли-је-обухваћена-судска-пракса) налазе се поред права, један комит по одлуци на дан када је
донета ([`switzerland/bund/caselaw`](https://github.com/lexifina/switzerland-caselaw)), и додају се засебно: `python3
tools/countries.py add switzerland/caselaw`. Одлука је пресуда, а не закон (`Kind: court`), па је алати изостављају из
свега што се тиче права, осим ако је изричито наведете. [`check_precedent`](FEATURES.md#check_precedent-mcpcheck_precedent)
каже да ли је текст који је одлука применила још увек на снази, а
[`resolve_citations`](FEATURES.md#resolve_citations-mcpresolve_citations) чита цитате у уобичајеном облику сваке земље
(`§ 823 Abs. 1 BGB`, `article 1240 du code civil`). [`manifest.json`](../../manifest.json) даје покривеност сваког суда.

> **Напомена за српско издање:** за Србију нема судске праксе, а алати `check_precedent` и `world_on_date` сакривени су у српском профилу сервера.

## Више

- [FEATURES.md](FEATURES.md): свака функција, и шта сваки корпус овде мора да подржава (`git blame`, `law.py`, MCP алати)
- [FAQ.md](FAQ.md): питања и одговори · [CONTRIBUTING.md](CONTRIBUTING.md): предлагање измена · [MCP.md](MCP.md): MCP сервер · [REPRODUCE.md](REPRODUCE.md): како је изграђено · [CHANGELOG.md](../../CHANGELOG.md)
- [FRESHNESS.md](FRESHNESS.md): колико је сваки корпус ажуран · [Праћење](../../monitoring/): да ли ажурирања раде · [WATCHING.md](WATCHING.md): како се сваки службени извор надгледа ради измена
- [Перформансе](../../performance/): колико брзо алати одговарају на вашем сопственом клону, једнократни показатељ · [Тестови](../../tests/): шта се проверава, покреће се са `python -m unittest discover -s tests`
- [Визуелизације](../../visualisations/): графикони и мостови кроз светско право
- [Рањивости](../../vulnerabilities/): грешке у прописима онако како су објављени
- [Видео-снимци](../../videos/): сваки видео-снимак који показује шта global-law ради, од његових функција и права једне земље до архиве на један датум и начина на који се проверавају ажурирања

## Видео-снимци

https://github.com/user-attachments/assets/6020acb1-53f3-4b65-94a4-fe132b867358

https://github.com/user-attachments/assets/6119b018-5f5b-4bab-a2da-0aad30ef585f

## Лиценца

Овај репозиторијум је под [CC0](../../LICENSE.md). Текст закона налази се у репозиторијуму сваке земље, под сопственим
условима тог репозиторијума.
