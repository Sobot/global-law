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

## Uputstva za asistente

Paket sadrži [tri uputstva (skills)](plugins/sr/skills/) za citiranje odredbe, utvrđivanje teksta koji je važio na određeni datum i poređenje verzija. Server ih izlaže kao MCP resurse koje klijent može da pročita.

## Poreklo projekta i licenca

Ovaj server je srpska adaptacija projekta [Global Law](https://github.com/lexifina/global-law). Tekstovi propisa i istorija izmena dolaze iz [korpusa za Srbiju](https://github.com/lexifina/serbia-law). Dokumentacija izvornog projekta opisuje [zajedničke alate i komande](FEATURES.md) i [globalni MCP interfejs](MCP.md).

Ovaj repozitorijum je objavljen pod [CC0](LICENSE.md). Za tekstove propisa važe uslovi navedeni u repozitorijumu korpusa.
