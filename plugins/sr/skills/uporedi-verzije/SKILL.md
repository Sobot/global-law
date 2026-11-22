---
name: uporedi-verzije
description: Uporedi dve verzije srpskog propisa ili člana i utvrdi šta je konkretna izmena dodala, obrisala, zamenila ili prenumerisala.
---

1. Utvrdi propis, obuhvat i dva datuma. Kada korisnik navede samo broj službenog glasila, pronađi odgovarajući akt o izmeni i proveri datum kada je konkretna odredba stupila na snagu. Kao početnu verziju uzmi tekst neposredno pre te promene.
2. Za jedan član na istoj putanji koristi `compare_dates` sa `path`, `date_a` i `date_b`. Za ceo akt počni pregledom pogođenih odredaba. Za konkretnu izmenu koristi `law_details` sa identifikatorom izmene iz rezultata. Ako je pregled skraćen, suzi obuhvat ili označi koje su odredbe proverene.
3. Otvori obe verzije pomoću `read_law`. Ako je član promenio broj ili putanju, pronađi njegov prethodni i novi tekst zasebno. Isti broj člana u dva zakona nije dovoljan dokaz kontinuiteta.
4. Za svaku materijalnu promenu prikaži kratko „pre“, „posle“ i posledicu koju tekst podržava. Označi čisto redakcijske izmene. Priloži datume i vraćene linkove za obe verzije i, ako postoji, link na samu izmenu. Ako jedna verzija nedostaje, označi poređenje kao delimično.
