---
name: pronadji-i-citiraj-odredbu
description: Koristi kada korisnik traži tačan član, stav ili tačku srpskog propisa, proveru navoda ili direktan link do citiranog teksta.
---

1. Pomoću `find_provision` pronađi propis po nazivu i broju člana. Proveri puni naziv akta. Ako upit bez dijakritika ili skraćenica ne daje rezultat, pokušaj pun naziv ćirilicom ili pretraži karakteristične reči pomoću `search_law`.
2. Otvori pronađenu putanju pomoću `read_law` za traženi datum ili za danas. U samom tekstu proveri član, stav i tačku. Ako je odgovor skraćen, učitaj nastavak. Razlikuj pravno numerisane jedinice od redova Markdown fajla.
3. Navedi pun naziv propisa, proverene jedinice i datum verzije. Prenesi relevantnu rečenicu u izvornom pismu, pa odvojeno iznesi tumačenje ako je traženo.
4. Priloži službenu referencu kada je dostupna i vraćeni `file_url` za pročitanu verziju. Ako postoji samo `commit_url`, označi ga kao link na izmenu. Ako nedostaje tražena tačka ili permalink, reci šta je potvrđeno i koji podatak nedostaje. Linkove preuzimaj iz rezultata alata.
