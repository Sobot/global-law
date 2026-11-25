<!-- upstream: REPRODUCE.md @ 8a81ec4d2256a865f829e97102652a8b52aa0641 -->
# Git за светско право: како се овај репозиторијум прави и како се проверава

> Превод оригинала [REPRODUCE.md](../../REPRODUCE.md) на српски.

> Овај клон користи јавни корпус [lexifina/serbia-law](https://github.com/lexifina/serbia-law) као подмодул `serbia/national/acts`; он се ажурира из upstream-а, а не гради поново овде. `.github/workflows/sync-freshness.yml` ажурира његов пин.

Овај фајл бележи како се репозиторијум прави и како свако може да га провери само помоћу git-а. Има два дела. Од
2. новембра 2026. репозиторијум расте искључиво fast-forward-ом: никада се не гради поново и ниједан већ објављени комит
се не замењује. До 29. октобра 2026. скрипта га је градила од нуле, а евиденција о томе чува се у наставку, у другом делу.

## Први део: како репозиторијум сада расте

```sh
git clone https://github.com/lexifina/global-law && cd global-law
python tools/verify.py                       # since the last clean run: every submodule has its .gitmodules entry
python tools/verify.py --full                # every commit (about 45 s)
python tools/verify.py --remote              # and every pin is on its repository's main and moved only forward
                                             # (first run about 4 minutes and 560 MB in .git/global-law-verify;
                                             # later runs check only what came after the last clean run)
python tools/describe.py --check             # manifest.json and the jurisdiction.json files match the tree
python -m unittest tests.test_law_fixtures   # how law.py reads a corpus, on small corpora built for the test
```

(Коментари у коду, редом: од последњег успешног покретања, сваки подмодул има свој унос у `.gitmodules`; сваки комит (око 45 s);
и сваки пин је на `main` грани свог репозиторијума и померан је само унапред (прво покретање траје око 4 минута и заузима 560 MB у
`.git/global-law-verify`; каснија покретања проверавају само оно што је дошло после последњег успешног покретања); `manifest.json`
и фајлови `jurisdiction.json` одговарају стаблу; како law.py чита корпус, на малим корпусима направљеним за тест.)

- **Шта комит ради.** Сваки комит од 2. новембра 2026. ради једну од три ствари:
  - додаје корпусе као подмодуле;
  - помера пинове корпуса на тренутне комитове њихових репозиторијума;
  - мења документацију и алате.

  Програм који покреће Lexifina прави прве две врсте отприлике на сваких неколико минута, како репозиторијуми држава објављују. Он није део овог репозиторијума.
- **Шта проверава пре сваког push-а.**
  - Пин се помера само унапред: нови комит потиче од старог. Репозиторијум државе који је преписан задржава се на свом последњем пину и пријављује се, а никада се не прати.
  - Сваки подмодул има свој унос у `.gitmodules` и сваки унос свој подмодул.
  - Push је обичан fast-forward, који се понавља из новог fetch-а ако је неки други комит стигао први.
- **Где корпус иде.** Сваки корпус иде тамо где га смешта његов сопствени `jurisdiction.json`:
  - `<country>/<level>/<corpus>` за национално или савезно право и за савезну државу или покрајину;
  - `<country>/<state>/<city>/acts` за град или округ (regency) унутар њих.

  `data/moved-paths.tsv` наводи корпусе премештене од тада, а алати читају стару путању са новог места.
- **Описи.** `manifest.json` и сваки `jurisdiction.json` пише `tools/describe.py` на основу корпуса закачених у том тренутку. Сваки корпус описују `corpus.json`, `data/repo.json` и `jurisdiction.json` његовог сопственог репозиторијума на закаченом комиту. `history` корпуса (in-force, replayed, as-enacted, current-only или metadata-only) узима се онако како га корпус декларише, у `corpus.json` или, ако га тамо нема, у `data/repo.json`. Само недекларисана историја изводи се из фајлова изградње, и тада `derived` то наводи. README који каже да се сваки акт чува онакав какав је донет даје `as-enacted`. `tools/check_corpus.py` одбија декларацију која није једна од ових вредности или којој комитови противрече (MCP.md).
- **Датуми.** Датуми се читају из сопствене историје сваког корпуса, како описују `tools/law.py` и README.md. Историја по законима из другог дела и даље је ту, замрзнута. Њени датуми за комитове корпуса који немају сопствене датуме чувају се у `data/legacy-dates.tsv`.
- **Шта се не може проверити.** Неки стари комитови закачују комитове корпуса које њихови репозиторијуми више не садрже. У историји из другог дела погођено је 1.400 пинова, међу њима и последњи пин 89 корпуса. Између 29. октобра и 2. новембра погођено је 2.503 пина. Ти репозиторијуми су преписани пре правила fast-forward. `git submodule update` на таквом комиту не успева за те корпусе и ништа у овом репозиторијуму то не може да поправи; `tools/verify.py --since <commit> --remote` их наводи по имену. GitHub и даље сервира већину ових комитова по њиховом хешу (свих 3.486 пинова постављених пре 2. новембра које ниједна грана не садржи могло је да се преузме 4. новембра 2026), али их ништа не чува: настали су пре чишћења приватног материјала, па су препуштени GitHub-овом сакупљању смећа (garbage collection); преузимање историје пре 2. новембра ради се по принципу најбољег покушаја. Десет пинова постављених 2. новембра после db84b4c није на `main` грани свог корпуса (uruguay и norway по 3; brazil, romania, greece и belgium по 1): сваки је истог дана замењен каснијим пином на `main`, и сваки фајл закона који садржи исти је у том каснијем пину, који код 4 од њих и додаје законе (један norway пин је исто стабло као један комит на `main`). Свих десет могло је да се преузме по хешу 4. новембра 2026, а ревизија push-а не налази приватни материјал у девет на којима је покренута (сви осим romania), али их ништа не чува. `tools/verify-known.tsv` их наводи уз разлог, а `tools/verify.py --remote` их наводи као познате уместо да пријави грешку; сваки други пин који `main` више не садржи и даље доводи до грешке.

## Други део: изградња од 28. и 29. октобра 2026. (замрзнуто)

До 29. октобра 2026. (комит `0e10db05b17`) овај репозиторијум је од нуле градила скрипта која је сада
`tools/archive/build-2026-10-29.py` (тада `tools/build.py`), сачувана бајт по бајт онаква каква је била. Та изградња се више не може
поновити хеш по хеш: већина репозиторијума држава које је читала преписана је 29. октобра, пре правила fast-forward, па
комитови које је закачила више нису сви објављени. Никада не објављујте њен излаз преко овог репозиторијума: заменио би
целу историју. Оно што следи је евиденција те изградње онако како је тада написана.

Скрипта се чува ради увида. Не може се покренути само из овог репозиторијума. Написана је да стоји у сопственом репозиторијуму
Lexifina-е, поред `check_corpus.py` (у тада испорученој верзији: blob `df05a76154489dda2f7644651b3c37bd009d773e` у
`0e10db05b17`, а не новији `tools/check_corpus.py`), фасцикле `repo/` са шаблонима README и REPRODUCE и фасцикле
`../world-law/` која садржи `countries.json`, `register.json` и `build_countries.py`. Само први је у овом
репозиторијуму. Она такође наводи корпусе помоћу `gh repo list lexifina`, клонира тренутну подразумевану грану сваког
репозиторијума уместо тада закаченог комита и чита тренутне пинове global-law-а ради провере да се само додаје (append-only),
тако да чак и са тим фајловима гради из данашњих репозиторијума, а не из комитова у табели испод. Онако како је тада покренута, из те фасцикле:

```sh
python scripts/global-law/build.py ../rebuilt --date 2026-10-28   # in Lexifina's repository, on 28-29 October 2026
```

(Коментар у коду: у репозиторијуму Lexifina-е, 28–29. октобра 2026.)

Без поновне изградње може се проверити да је табела испод управо оно што је закачио последњи поново изграђени комит и да је
архивирана скрипта управо она коју тај комит испоручује:

```sh
git fetch --depth 1 origin 0e10db05b17774b0ac8c07aa79c51ef353141cac
git ls-tree -r 0e10db05b17 | awk '$2=="commit"{print $4" "$3}' | sort > pins-built.txt
sed -n 's/^| `\([^`]*\)` | [^|]* | `\([0-9a-f]*\)` |$/\1 \2/p' REPRODUCE.md | sort > pins-claimed.txt
diff pins-built.txt pins-claimed.txt && echo "the 107 pins match"
git show 0e10db05b17:tools/build.py | git hash-object --stdin   # d1b094cb56666f87012d2e7ddf3a6d746042c176
git ls-files -s tools/archive/build-2026-10-29.py                 # the same blob
```

(Команде се покрећу на оригиналном `REPRODUCE.md` у корену репозиторијума. Коментар у последњем реду: исти blob.)

Дана 28. октобра 2026. две изградње у одвојене празне фасцикле дале су истих 339326 хешева комитова, од првог комита
(стабло јурисдикција, са датумом 1. јануар 1970) до последњег (та документација).

### Из чега је изграђен

Овај репозиторијум не садржи сопствени правни текст. Изграђен је из 107 репозиторијума, од којих сваки има свој
REPRODUCE.md који бележи како је његов текст прибављен. У време ове изградње били су на следећим комитовима, а то су комитови које је овај
репозиторијум закачио при тој изградњи (а не данашњи пинови на HEAD-у, које наводи manifest.json):

| Путања овде | Репозиторијум | Комит |
| --- | --- | --- |
| `albania/national/acts` | https://github.com/lexifina/albania-law | `20f957b4cc6944d4fcc51323cc267d1c7b90d67f` |
| `armenia/national/acts` | https://github.com/lexifina/armenia-law | `3f01702f5e6b6d78e4f47db55ddb863d8126c80f` |
| `angola/national/acts` | https://github.com/lexifina/angola-law | `1a73c1569157f6e09708df5b3ea2bab08c500a23` |
| `argentina/national/acts` | https://github.com/lexifina/argentina-law | `bc9bd216dacb9c84554b63de510a7eed3068537c` |
| `austria/bund/acts` | https://github.com/lexifina/austria-law | `4cc372aef9323b9fb5b0478ba4d925e8dcb21863` |
| `australia/federal/acts` | https://github.com/lexifina/australia-law | `e1bfa28e888e409a17dd42f64b6a1d95d2226d71` |
| `aland/national/acts` | https://github.com/lexifina/aland-law | `684156dfc5ce445ad2f1bc0adec9c5cf998c5c08` |
| `azerbaijan/national/acts` | https://github.com/lexifina/azerbaijan-law | `08f3d7e2f1eafd21e084bf73931d346903553599` |
| `bulgaria/national/acts` | https://github.com/lexifina/bulgaria-law | `476e565a2760b862c90fc1b9efd1772d666ef248` |
| `bolivia/national/acts` | https://github.com/lexifina/bolivia-law | `bd90e24991b39b706cc4ec008f4ce27784c0720c` |
| `brazil/national/acts` | https://github.com/lexifina/brazil-law | `09db458187d61fe69368717bce8363efe15d7d0d` |
| `bahamas/national/acts` | https://github.com/lexifina/bahamas-law | `b13688b3b421f479ae819f752900eedf08da2209` |
| `botswana/national/acts` | https://github.com/lexifina/botswana-law | `8e6f8772441eb074e7c33caffa409873bf48f6c2` |
| `canada/federal/acts` | https://github.com/lexifina/canada-law | `60a8dcfa31b90a40b314d922fca8104a0ecb2070` |
| `canada/northwest-territories/acts` | https://github.com/lexifina/canada-northwest-territories-law | `7541f87ffb89e96952c3a1949a3b03a5e4f270ff` |
| `dr-congo/national/acts` | https://github.com/lexifina/dr-congo-law | `cb1f4afcee5c1647cbf0eba273b26cc2180c4316` |
| `switzerland/bund/acts` | https://github.com/lexifina/switzerland-law | `06696ea19cf23d362f02ac688ff59df3fdb14aab` |
| `cote-divoire/national/acts` | https://github.com/lexifina/cote-divoire-law | `16ef33c9b6264afe1a55a5a806d1f1b1a0ce1b10` |
| `cook-islands/national/acts` | https://github.com/lexifina/cook-islands-law | `00d1944e525eb0e2fe56db0504184e0ab8fd7f2c` |
| `chile/national/acts` | https://github.com/lexifina/chile-law | `338d336fe2d471e959f3724b3b682280e9cdbd02` |
| `china/national/acts` | https://github.com/lexifina/china-law | `334c5528af9b757e5d22e6740c0b7d2a1e86672a` |
| `colombia/national/acts` | https://github.com/lexifina/colombia-law | `5034ffb6af541d9008097668e8b3e37b03b7793d` |
| `cyprus/national/acts` | https://github.com/lexifina/cyprus-law | `8e6847e4a151b2795d4d9b536c0622d736a52f33` |
| `czechia/national/acts` | https://github.com/lexifina/czechia-law | `35e53bb38ca677a77c3a0ea218b6db7dce7cf89d` |
| `germany/bund/acts` | https://github.com/lexifina/germany-law | `6f3913a35a8ed38c01d9f1919fa1e3af0ba01f9f` |
| `denmark/national/acts` | https://github.com/lexifina/denmark-law | `0217682e8e5aa69182148d5249c3bd7b61e098c3` |
| `dominican-republic/national/acts` | https://github.com/lexifina/dominican-republic-law | `e3bf2d77e19b6f4af532ef07dfff8044382a64a1` |
| `ecuador/national/acts` | https://github.com/lexifina/ecuador-law | `d29cefecfb59530e840b484280bcc112f045c577` |
| `estonia/national/acts` | https://github.com/lexifina/estonia-law | `91c786e18330af4b6cb5b04323c7b92532f7f912` |
| `spain/national/acts` | https://github.com/lexifina/spain-law | `513d8526e652a8ca81e9239aab5154040d6f9ad8` |
| `finland/national/acts` | https://github.com/lexifina/finland-law | `86af6a1257d27a7d97528c9154a515fb42a22e33` |
| `fiji/national/acts` | https://github.com/lexifina/fiji-law | `3ce68fd71d38a5e3eb7f6301a7ae28f9bbd9222d` |
| `micronesia/national/acts` | https://github.com/lexifina/micronesia-law | `e47ba7a924d2b9b1ea993cfe909f9e3b7ef3efc1` |
| `france/national/acts` | https://github.com/lexifina/france-law | `a6e16b131b5821792b172eab692c860339397a51` |
| `united-kingdom/uk/legislation` | https://github.com/lexifina/united-kingdom-law | `2d4137c6246be7396dc1fc930b71ccd6aa9f75a7` |
| `georgia/national/acts` | https://github.com/lexifina/georgia-law | `ef77971d51e67faddd63178df242f546890d9ce5` |
| `ghana/national/acts` | https://github.com/lexifina/ghana-law | `28341b4407ac073ea730d1232ae77c297c63dfd6` |
| `gibraltar/national/acts` | https://github.com/lexifina/gibraltar-law | `ecddb5d0851f29c189eadb18c6cccba9965b97b9` |
| `greenland/national/acts` | https://github.com/lexifina/greenland-law | `e132142bb86dc9346234fe7ca7d6c96507b6c644` |
| `guinea/national/acts` | https://github.com/lexifina/guinea-law | `1528198d92d503a26d328d484e4df512e993eaef` |
| `greece/national/acts` | https://github.com/lexifina/greece-law | `ccf04e0190b175e1ea575654d2c3e7de61754a28` |
| `guyana/national/acts` | https://github.com/lexifina/guyana-law | `f5149ae7b7fcebba40ab001c7ea5036198125ded` |
| `hong-kong/national/acts` | https://github.com/lexifina/hong-kong-law | `63e41dfab5e6d4ce55ce9227dfed3dbc66f41aee` |
| `croatia/national/acts` | https://github.com/lexifina/croatia-law | `309ababd219a2b68480b24561579aa6c9b4adc9c` |
| `ireland/national/acts` | https://github.com/lexifina/ireland-law | `75f491b4911cd4ee016ba918526cf149687cddeb` |
| `italy/national/acts` | https://github.com/lexifina/italy-law | `38f884dd1eb91c95cfafb419528d77da30b8fb87` |
| `japan/national/acts` | https://github.com/lexifina/japan-law | `9df83c895787f1b398320041c8436c03aee86342` |
| `kenya/national/acts` | https://github.com/lexifina/kenya-law | `f9a6d26f99d017720cc2a69c704de0abfabf9440` |
| `kyrgyzstan/national/acts` | https://github.com/lexifina/kyrgyzstan-law | `74da05a27ee87e06ed440285c008b240e0ba342f` |
| `liechtenstein/national/acts` | https://github.com/lexifina/liechtenstein-law | `9643f48ffeb106e8a5ae104e776b814a550d1ce1` |
| `liberia/national/acts` | https://github.com/lexifina/liberia-law | `18744e71d894313d039e30214aaf886ca950e05a` |
| `lesotho/national/acts` | https://github.com/lexifina/lesotho-law | `2da8f55d9e0aa3020d111f89337b7e7fa14fcdc5` |
| `lithuania/national/acts` | https://github.com/lexifina/lithuania-law | `72337dff7442839dc54afa2d4364b8275390568a` |
| `luxembourg/national/acts` | https://github.com/lexifina/luxembourg-law | `16ebb76ea19ffd8b47b9313e585fe56c132f3bdc` |
| `latvia/national/acts` | https://github.com/lexifina/latvia-law | `93a3acd41c240bdc6b89f688e5372480c5ee4903` |
| `monaco/national/acts` | https://github.com/lexifina/monaco-law | `04f2f086a9bdd71710fe7a0938e24cdb906dda95` |
| `moldova/national/acts` | https://github.com/lexifina/moldova-law | `383eb470e35fd45cd6ee593c56f5e8b902a547c8` |
| `montenegro/national/acts` | https://github.com/lexifina/montenegro-law | `cf16b160e81453d81588314e5d2fae83d38dac0d` |
| `madagascar/national/acts` | https://github.com/lexifina/madagascar-law | `6158f55667e3a8654fcb2be6099560f75e668e84` |
| `north-macedonia/national/acts` | https://github.com/lexifina/north-macedonia-law | `7a6625e9d6398c8071fab8f0b16d56ed63154325` |
| `mali/national/acts` | https://github.com/lexifina/mali-law | `64d3d6203b4fbde3b908a302687d5d34c34fa04a` |
| `mongolia/national/acts` | https://github.com/lexifina/mongolia-law | `c98d57460c70e29bece8e24efcb3bffb78a4ceb7` |
| `malta/national/acts` | https://github.com/lexifina/malta-law | `7d25128590327a1ec6845f2ecd179b223bcf6a8f` |
| `malawi/national/acts` | https://github.com/lexifina/malawi-law | `2a966219d3150d1ecdaf9f047455a642c6b3eb0f` |
| `mexico/national/acts` | https://github.com/lexifina/mexico-law | `18ee6918ba0c678f6e8a05803633b372af782f97` |
| `malaysia/national/acts` | https://github.com/lexifina/malaysia-law | `91ac23b7c1912ef57ab72afba32df68b9e4e2e83` |
| `namibia/national/acts` | https://github.com/lexifina/namibia-law | `054b4743b3688004781b94c8f852524f908d61f3` |
| `nigeria/national/acts` | https://github.com/lexifina/nigeria-law | `3176a08ec3072c385e7a3ba239df52415625dc2c` |
| `nicaragua/national/acts` | https://github.com/lexifina/nicaragua-law | `ec69becd3a541d4f099e37216787faaa8b77226a` |
| `netherlands/national/acts` | https://github.com/lexifina/netherlands-law | `fdb8e5f31cf5c5542583b4eb45da3fc8dfe59f17` |
| `norway/national/acts` | https://github.com/lexifina/norway-law | `48705e7b50710fbbc0783ec95bf2be811cdc1014` |
| `new-zealand/national/acts` | https://github.com/lexifina/new-zealand-law | `f505ca6cae1468ce1d95f54e19340cd011d79630` |
| `peru/national/acts` | https://github.com/lexifina/peru-law | `8cd72cdce372ef0f90115067b6384fef6b69f376` |
| `poland/national/acts` | https://github.com/lexifina/poland-law | `7c0f3010a5a9daa6b307d9b10e05cc9b58901145` |
| `portugal/national/acts` | https://github.com/lexifina/portugal-law | `88c02e7aefc1ebeeb89911621a546734ae1240bc` |
| `palau/national/acts` | https://github.com/lexifina/palau-law | `dfe9d8de52cfb653190c31a8096fd970cef24ef2` |
| `paraguay/national/acts` | https://github.com/lexifina/paraguay-law | `90d7d58c4b0a5c5e3b545ef8918e7c94754128ca` |
| `romania/national/acts` | https://github.com/lexifina/romania-law | `ec269e743705364291b7fb6eba86a3d974ef11a0` |
| `rwanda/national/acts` | https://github.com/lexifina/rwanda-law | `121603ed4b20bcbdc22a8a93f0be713d86725b51` |
| `saudi-arabia/national/acts` | https://github.com/lexifina/saudi-arabia-law | `65f6fcf944ba04a7470912eeeaca496af3d82f41` |
| `seychelles/national/acts` | https://github.com/lexifina/seychelles-law | `eaf8ae00362f313df431e472dc852b3a45f986df` |
| `sweden/national/acts` | https://github.com/lexifina/sweden-law | `4073fa45f0bce755acab0507fca7247418920081` |
| `slovenia/national/acts` | https://github.com/lexifina/slovenia-law | `9387d5b524938a84486b20d616799e4134f2727f` |
| `slovakia/national/acts` | https://github.com/lexifina/slovakia-law | `a595c0404742d62ddadf2efe589646b5eaa0b09f` |
| `sierra-leone/national/acts` | https://github.com/lexifina/sierra-leone-law | `43292116fe4ab95dcda6ee0bbe3b8755cd7615a8` |
| `senegal/national/acts` | https://github.com/lexifina/senegal-law | `813c104879cd6d1b4c4a336733d5a40ce288fb43` |
| `suriname/national/acts` | https://github.com/lexifina/suriname-law | `f8bf52f5a8b1fcf96f69ef5be5294c17805a4b37` |
| `eswatini/national/acts` | https://github.com/lexifina/eswatini-law | `d0652e05b270a0070323a4c9c514d2432972980b` |
| `togo/national/acts` | https://github.com/lexifina/togo-law | `10b1d016ebd4e8fd69daa3414a9f100a2ed8efed` |
| `thailand/national/acts` | https://github.com/lexifina/thailand-law | `3f8fce0c6635742b347d4879f1acaa57b7ec8e0b` |
| `timor-leste/national/acts` | https://github.com/lexifina/timor-leste-law | `46095bfa4b4bad5d114b81cf94b8345629dd9785` |
| `turkey/national/acts` | https://github.com/lexifina/turkey-law | `7bd09670654aa06019eb03d4cae668be80b62705` |
| `taiwan/national/acts` | https://github.com/lexifina/taiwan-law | `1ed84a25e45679acade7d716361cc328d2a572c1` |
| `tanzania/national/acts` | https://github.com/lexifina/tanzania-law | `165e15932def1eac105570861a020e41c3e23c90` |
| `uganda/national/acts` | https://github.com/lexifina/uganda-law | `464b01f39153f6a55b05f36455fec4f60cc984e6` |
| `united-states/california/statutes` | https://github.com/lexifina/united-states-california-law | `a7096690ee942d855625bdf5076b870cc684615f` |
| `united-states/district-of-columbia/statutes` | https://github.com/lexifina/united-states-district-of-columbia-law | `dd1fc3d82cd99755f0bedb4ceab9783cb4682fb3` |
| `united-states/federal/usc` | https://github.com/lexifina/united-states-law | `f5537151bfb3ee25c86e87c70f945fbcf6ffd611` |
| `united-states/indiana/statutes` | https://github.com/lexifina/united-states-indiana-law | `be5bfc582f1b21511920327d4510343137e246d6` |
| `united-states/new-jersey/statutes` | https://github.com/lexifina/united-states-new-jersey-law | `ae730bf98d9fe4b4cbe81cc17d425e48e6f1a83e` |
| `united-states/utah/statutes` | https://github.com/lexifina/united-states-utah-law | `000b9edcd1e44a6b69b6ae7b7132234e145e133c` |
| `uruguay/national/acts` | https://github.com/lexifina/uruguay-law | `37b6df4990347f183ac006dc389d6207350b710f` |
| `vatican-city/national/acts` | https://github.com/lexifina/vatican-city-law | `b07b82ef75b99b6a3b953e2dfcf8cfb53b5766d7` |
| `venezuela/national/acts` | https://github.com/lexifina/venezuela-law | `53ea22646e6f2a52a9157974732c593e42750b60` |
| `south-africa/national/acts` | https://github.com/lexifina/south-africa-law | `5d4c44b126564d5f38ab9014855708fe7d475836` |
| `zambia/national/acts` | https://github.com/lexifina/zambia-law | `5ad4a6ec9d3881cdfb98da3fefd53a82fb0b8721` |
| `zimbabwe/national/acts` | https://github.com/lexifina/zimbabwe-law | `e7a3c9bfe4b0e44b1366f2f6c3278cb67fe2a3f6` |

Изградња чита комитове сваког репозиторијума на линији првих родитеља (first-parent) његове подразумеване гране, са њиховим ауторима, датумима
и трејлерима порука, као и његове ознаке (tags). Такође чита `corpus.json` (или `data/repo.json`) сваког репозиторијума на том комиту, наводи
репозиторијуме организације помоћу `gh` и чита сопствене пинове global-law-а са GitHub-а.

### Изградња, корак по корак

Скрипта за изградњу била је `tools/build.py`, сада `tools/archive/build-2026-10-29.py`. То је фајл који комит `0e10db05b17` испоручује као
`tools/build.py` (git blob `d1b094cb56666f87012d2e7ddf3a6d746042c176`). Алат за читање `tools/law.py` има blob
`a4eed065182fff59d22f60f5f5a595435047eb19`, а тестови `tests/test_law.py` имају blob
`b8f530cdac1abe5b1631b88d42f01c4de1dd0bcc`.

1. `python scripts/global-law/build.py <out> --date 2026-10-28 --site-data saas-webpage/app/watch/global-law/_data/global.json`
   - прави bare клон сваког репозиторијума корпуса у `<out>/.git/corpus-cache/`
   - пише први комит (стабло јурисдикција, `manifest.json` и `.gitmodules`)
   - пише по један комит за сваки комит корпуса, по редоследу ступања на снагу, при чему сваки помера пин тог корпуса
   - копира ознаке сваког корпуса под његову путању
   - пише последњи комит са README-ом, овим фајлом, алатима и тестовима
   - и, са `--site-data`, пише временску линију коју чита страница на lexifina.com/watch/global-law
2. Иста команда у другу празну фасциклу. `git log --format=%H` био је идентичан у обе: 339326 комитова.
3. `git submodule update --init`, затим `python -m unittest discover -s tests -v`. Свих 48 тестова је прошло.
4. `git push --force -u origin main` и `git push --force origin --tags` објавили су га на GitHub-у. Тада је то био приватни
   репозиторијум; сада је јаван.
5. Нови `git clone --recurse-submodules` са GitHub-а, а затим поново тестови. Сви су прошли.

Изградња и алати користе само стандардну библиотеку Python-а и git. Покретани су са Python 3.12.10 и git
2.46.0 на Windows 11. Ниједан AI модел нити друга услуга не учествују у изградњи или читању историје.

### Како је та историја изведена

Све у наставку урадила је скрипта за изградњу, детерминистички. Исти комитови корпуса дају исте хешеве.

- **Путање.** Сваки корпус се налази под државом (ISO 3166-1), затим нивоом, затим корпусом:
  - `germany/bund/acts`
  - `united-kingdom/uk/legislation`
  - `united-states/federal/usc`

  Подређени (субнационални) ниво користио би свој ISO 3166-2 код, на пример `us/ca`. Свака фасцикла изнад корпуса садржи
  `jurisdiction.json` који је именује и наводи њену децу.
- **Редослед.** Комитови корпуса спајају се по датуму ступања на снагу, уз задржавање сопственог редоследа сваког корпуса. Сваки
  корпус бележи свој датум ступања на снагу у трејлеру:
  - `In-force:` за корпусе САД и Уједињеног Краљевства
  - `In-Kraft:` за Grundgesetz

  Комит корпуса без њега (почетно издање или документација) смешта се према датуму аутора.
- **Комитови.** Овде постоји по један комит за сваки комит корпуса.
  - Име, адреса и датум аутора су они из комита корпуса. За Grundgesetz пре 1970. тај датум је
    ограничен на 1970, јер git не може да чува раније датуме.
  - Committer је `Lexifina <global-law@lexifina.com>`, са истим датумом.
  - Тамо где би датум пао пре датума родитеља, подиже се на датум родитеља, тако да датуми комитова никада не иду
    уназад.
  - Трејлери су `Corpus`, `Corpus-commit`, `Law`, `In-force` и `Kind` (law, baseline или documentation). Алати
    се ослањају на `In-force`, никада на датум комита.
- **Ознаке.** Свака ознака корпуса копира се као `<path>/<tag>`, на пример `germany/bund/acts/gg/36`, и показује на
  комит овде који је померио корпус на означени комит.

### Одлуке донете ручно

1. **Фасцикле изнад корпуса, а не репозиторијуми.** Угњеждени репозиторијуми би учинили да се свака измена преноси навише кроз
   пин сваког нивоа. Фасцикле дају исто стабло са једним нивоом подмодула.
2. **Овде један комит по комиту корпуса,** а не један по дану. Тако је сваки комит један закон који ступа на снагу,
   а његов аутор је тај закон.
3. **Изградња подразумевано чита објављене репозиторијуме.** Једна ранија изградња читала је локални checkout и закачила
   комит који није био push-ован, па нови клон није могао да га преузме. Изградња из локалних checkout-а
   (`--local`) задржана је ради испробавања измене корпуса пре него што се push-ује. Таква изградња се не објављује.
4. **Шта није у git-у.** Две ствари које приказују Lexifina читачи јесу израчунати подаци, а не историја:
   - које друге одредбе користе дефинисани појам или наводе одељак
   - обавештења за одељак који се прати

   Ниједно није у овом репозиторијуму. Ретроактивни домашај каснијег закона налази се само у порукама комитова корпуса и не
   мења текст приказан за раније датуме.

### Шта је урадио AI модел

Овај репозиторијум изграђен је 28. октобра 2026. у **Claude Code**, Anthropic-овом алату за програмирање, помоћу модела **Claude Opus
5.5** (идентификатор модела `claude-opus-5-5`). Модел је радио на основу циља који је поставио корисник у Lexifina-и: да осмисли git
репозиторијум „светског права“, са јурисдикцијама у њему и правом сваке од њих унутар њих, изграђен из постојећих
репозиторијума корпуса Lexifina-е, а затим да га тестира и објави страницу о њему.

Модел је:

- **Изабрао дизајн** описан изнад и у README-у, након што је прочитао комитове, трејлере и ознаке
  три репозиторијума корпуса.
- **Написао сав код и текст у овом репозиторијуму:** `tools/build.py`, `tools/law.py`, `tests/test_law.py`,
  README и овај фајл.
- **Покренуо команде наведене изнад** и проверио резултате: тестове, две изградње упоређене хеш по хеш и
  нови клон са GitHub-а.

Модел **није**:

- **Написао нити изменио било какав правни текст.** Овај репозиторијум га не садржи. Текст је у репозиторијумима корпуса, где су га
  њихове сопствене скрипте копирале од званичних издавача, како бележе њихови фајлови REPRODUCE.md.
- **Учествовао у изградњи или читању историје.** Изградња, алати и тестови не позивају ниједан AI модел.

Корисник је одлучио о обиму, власнику (организација Lexifina) и о томе да репозиторијум буде приватан (сада је јаван). Рад
није прегледао правник ред по ред. За све што је важно треба читати сам пропис.

### Тадашњи тестови

`tests/test_law.py` има 48 тестова:

- **Стабло.** Сваки ниво описује себе и своју децу, а head закачује сваки корпус на његов најновији комит.
- **Временска линија.**
  - Поређана је по редоследу ступања на снагу, са по једним комитом овде за сваки комит корпуса.
  - Сваки комит помера тачно један пин.
  - Датуми комитова никада не иду уназад.
- **Читања на датум.**
  - Амерички лимит за дужника малог предузећа (small business debtor) износи 7,5 милиона долара 2021, нестаје у мају 2022, враћа се у јулу 2022 и нестаје у
    јулу 2024.
  - Grundgesetz Art. 12a појављује се од 28. јуна 1968, а Art. 91e од 27. јула 2010.
  - Пре 24. маја 1949. ништа није на снази.
  - Сваки корпус се поклапа са читањем самог тог корпуса на шест датума.
- **У поређењу са сопственим алатима сваког корпуса.**
  - Grundgesetz: шест чланова на седам датума од 1949. до 2017. слаже се са корпусовим `tools/stand_am.py`.
  - UK: свака верзија у корпусовом `data/history.json`, коју је приказао корпусов сопствени builder, једнака је фајлу
    прочитаном овде на датум те верзије.
- **Питања читаоца.**
  - `log`: сваки закон који је мењао фајл, по реду, са датумом ступања на снагу, датумом доношења и датумом објављивања.
  - Датуми који се разликују: SEND Regulations донети су 4. јуна, а ступили су на снагу 1. септембра 2014.
  - `blame` наводи закон у свакој јурисдикцији, а `words` приписује сваку реч: враћени §1182(1) закону Pub. L.
    117-151, Art. 79 и 1949. и 1954. години, једну реч reg. 13(3) прописима о коронавирусу из 2020.
  - Копиране ознаке показују на одговарајуће стање.
  - Обични `git ls-tree` и `git show` дају исти текст као алати.
  - Временски период наводи законе из две државе по реду.

## Измене овог репозиторијума након објављивања

- **28. октобар 2026.** Репозиторијум је премештен са личног налога у организацију Lexifina, а репозиторијуми корпуса
  су следили. Поново је изграђен са новим адресама и force-push-ован, а касније и са овим фајлом и
  додатом скриптом за изградњу.
- **29. октобар до 2. новембар 2026.** Репозиторијуми држава очишћени су од приватног материјала и преписани, а
  овај репозиторијум је престао да се поново гради: сваки комит од тада додаје корпусе или помера пинове (први део).
- **2. новембар 2026.** Од тада нема force-push-а, ни овде ни у било ком репозиторијуму државе, без сагласности власника за
  тај репозиторијум.
- **3. новембар 2026.** `tools/build.py` премештен је, непромењен, у `tools/archive/build-2026-10-29.py`; додати су `tools/verify.py`
  и `tools/describe.py`; 173 корпуса премештена су у фасцикле које даје њихов сопствени `jurisdiction.json`
  (`data/moved-paths.tsv`).
