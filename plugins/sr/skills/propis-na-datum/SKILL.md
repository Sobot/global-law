---
name: propis-na-datum
description: Utvrdi koji je propis ili tekst odredbe važio ili se primenjivao na određeni datum u Srbiji. Koristi i kada korisnik navodi današnji član za stariji događaj.
---

1. Izdvoji vreme događaja i pravno pitanje. Ako je navedena samo godina, proveri da li se relevantni tekst menjao tokom te godine. Ako jeste, prikaži periode ili zatraži datum događaja.
2. Identifikuj akt koji je tada uređivao materiju. Pomoću pretrage na datum proveri istorijski naziv, prethodni propis i, kada je relevantno, savezni propis. Današnji broj člana koristi kao trag. Kod promene numeracije proveri vezu kroz sadržaj odredbe ili akt o izmeni.
3. Pozovi `read_law` sa potvrđenom putanjom i datumom u obliku YYYY-MM-DD. Pomoću `provision_history` i po potrebi `law_details` proveri granice verzije, službenu referencu i datum stupanja na snagu. Proveri početak primene i prelazne odredbe ako odgovor zavisi od konkretnog postupka. Datum Git komita sam po sebi ne dokazuje nijedan pravni datum.
4. Navedi datum ili interval, tadašnji naziv i broj člana, relevantan tekst, službeni izvor (`cite.official_url` ili `source_links`) i vraćeni `file_url` na istorijsku verziju. Razlikuj službeni tekst verzije od izvora izmene. Ako korpus počinje kasnije ili nedostaje prethodni akt, navedi granicu podataka. Iz praznog rezultata ne izvodi zaključak da pravilo tada nije postojalo.
