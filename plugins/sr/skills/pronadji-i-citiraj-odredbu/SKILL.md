---
name: pronadji-i-citiraj-odredbu
description: Koristi kada korisnik traži tačan član, stav ili tačku srpskog propisa, proveru navoda ili direktan link do citiranog teksta.
---

1. Pomoću `find_provision` pronađi propis po nazivu i broju člana. Proveri puni naziv akta. Ako upit bez dijakritika ili skraćenica ne daje rezultat, pokušaj pun naziv ćirilicom ili pretraži karakteristične reči pomoću `search_law`.
2. Otvori pronađenu putanju pomoću `read_law` za traženi datum ili za danas. U samom tekstu proveri član, stav i tačku. Ako je odgovor skraćen, učitaj nastavak. Razlikuj pravno numerisane jedinice od redova Markdown fajla.
3. Navedi pun naziv propisa, proverene jedinice i datum verzije. Prenesi relevantnu rečenicu u izvornom pismu, pa odvojeno iznesi tumačenje ako je traženo.
4. Prvenstveno citiraj službeni izvor (`cite.official_url` ili `source_links`/`sources`). Razlikuj `Consolidated` (verzija teksta) od `Source` (izvor evidentirane izmene). Dodaj `file_url` za pročitanu verziju i `commit_url` kao link na izmenu. Ako službeni izvor ili tražena tačka nedostaje, reci to. Linkove preuzimaj iz rezultata alata.
