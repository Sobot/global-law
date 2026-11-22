# Закон: MCP за прописе Републике Србије

**Српски** · [English (upstream)](../README.md)

Питајте асистента како гласи члан закона, који текст је важио на одређени датум или шта се променило између две верзије. Сваки одговор можете проверити преко линка на текст члана у одговарајућој верзији или на измену која га је увела.

Ово је српско издање пројекта [Global Law](https://github.com/lexifina/global-law): право као Git историја, у којој сваки комит представља један пропис који ступа на снагу. Издање чита само прописе Републике Србије ([lexifina/serbia-law](https://github.com/lexifina/serbia-law)) и додаје српски MCP профил, претрагу ћирилицом и латиницом, линкове на изворе и вештине за асистенте.

## Повезивање

У клијенту који подржава удаљене MCP сервере додајте конектор са следећим подацима:

| Поље | Вредност |
| --- | --- |
| Назив | `zakon` |
| Тест MCP URL | `https://d38cy0uwrxlk77.cloudfront.net/mcp` |
| Транспорт | Streamable HTTP |

Ако отворите овај клон у VS Code-у, [`.vscode/mcp.json`](../.vscode/mcp.json) већ повезује тест сервер. Claude Code, Cursor и Codex покрећу локални сервер из клона ([MCP.md](../docs/sr-Cyrl/MCP.md)).

## Примери питања

> @zakon Kako je glasio čl. 21 st. 1 ZKP 29. maja 2019? Daj mi link na izvor.

> @zakon Упореди члан 21 ЗКП како је гласио 28. и 29. маја 2019. Прикажи само шта се променило и дај линкове на обе верзије.

> @zakon Која измена ЗКП-а је објављена у „Сл. гласнику РС“, бр. 35/2019? Дај ми линк на измену.

## Документација

| Документ | Садржај |
| --- | --- |
| [SRBIJA.md](../docs/sr-Cyrl/SRBIJA.md) | **могућности српског издања**: MCP профил, референце, индекс претраге, вештине, CI/CD, тестови |
| [README.md](../docs/sr-Cyrl/README.md) | превод основног описа пројекта Global Law |
| [MCP.md](../docs/sr-Cyrl/MCP.md) | MCP сервер, повезивање клијената и сви алати |
| [FEATURES.md](../docs/sr-Cyrl/FEATURES.md) | све функције и команде |
| [FAQ.md](../docs/sr-Cyrl/FAQ.md) | питања и одговори |
| [CONTRIBUTING.md](../docs/sr-Cyrl/CONTRIBUTING.md) | како предложити измену |
| [REPRODUCE.md](../docs/sr-Cyrl/REPRODUCE.md) · [FRESHNESS.md](../docs/sr-Cyrl/FRESHNESS.md) · [MONITORING.md](../docs/sr-Cyrl/MONITORING.md) · [WATCHING.md](../docs/sr-Cyrl/WATCHING.md) | како је корпус настао, колико је ажуран и како се прати |

Енглески оригинали остају у корену репозиторијума, исти као у upstream-у. Преводи у `docs/sr-Cyrl/` бележе комит оригинала из ког су настали, а `python tools/check_translations.py` наводи оне које треба ажурирати.

## Лиценца

Овај репозиторијум је објављен под [CC0](../LICENSE.md). За текстове прописа важе услови наведени у [репозиторијуму корпуса](https://github.com/lexifina/serbia-law).
