# Serbia Law MCP

Probna verzija zasnovana na `lexifina/global-law`. Čita samo `serbia/national/acts` sa punom istorijom.

## Lokalno pokretanje

```sh
git submodule update --init serbia/national/acts
python -m pip install -r requirements-serbia.txt
python -m uvicorn serbia_http:app --app-dir tools --port 8080
```

Endpoint: `/mcp` (Streamable HTTP); `/health` (provera spremnosti). STDIO: `sh tools/mcp.sh`.

## Reference

Relevantni odgovori dodaju `commit_url` uz konkretnu izmenu i `file_url` uz verziju člana kada odgovarajući MD fajl postoji u commitu. `read_law` čuva postojeća pravna polja, a `law_details` i dalje vraća originalne `message`, `trailers` i `trailers_all`, uz `provision_files` sa permalinkovima prvih 60 izmenjenih članova i oznaku `provision_files_truncated` ako ih ima više. Ostali alati ne dupliraju trailere.

`search_law` i `list_provisions` daju link na verziju člana za datum upita. `find_provision` nema istorijski datum i njegov link pokazuje na pin korpusa, ne na pojedinačnu izmenu. `In-force` je pravni datum, a ne datum Git commita. Zvanične reference ostaju primarni pravni izvor; GitHub linkovi služe proveri verzije u korpusu.

## CI/CD

Workflow `serbia.yml` koristi mali runtime image iz GHCR, čiji tag zavisi samo od Dockerfile-a i Python zavisnosti. Source i pin srpskog korpusa testiraju se u tom image-u. Na rasporedu se osvežava samo pin korpusa; ako iste verzije već rade, deployment preskače restart.

Na grani `main` deployment koristi postojeći AWS OIDC role, Systems Manager i `tools/deploy_serbia_test.sh`. EC2 zadržava kompletan checkout u `/opt/serbia-law-mcp`; Git istorija se inkrementalno preuzima, a `.git/global-law-cache` ostaje na disku između deploymenta. Checkout je u kontejneru read-only, dok je samo cache upisiv. Ako GHCR nije dostupan, na instanci se gradi samo runtime iz dva ulazna fajla. Neuspešan deployment vraća prethodne Git pinove i kontejner.

Kontejner sluša samo na lokalnom portu 8080 instance; nginx i CloudFront omogućavaju HTTPS. Za lokalni Docker test prvo inicijalizujte srpski submodule i montirajte checkout i cache isto kao CI (videti workflow).

## Test

```sh
python -m unittest discover -s tests -p test_serbia_refs.py -v
```

Testovi koriste stvarnu izmenu ZKP-a iz Sl. glasnika RS 35/2019.

## Skillovi

Paket za srpski jezik je u `plugins/sr/`. Novi postupak definišite u
`skills/<naziv>/SKILL.md` unutar paketa. U YAML zaglavlju navedite `name`
(isto kao naziv direktorijuma) i `description` (kada koristiti postupak).
Manifest i MCP konfiguracija nalaze se u korenu paketa.

Posle restarta server izlaže iste dokumente kroz `resources/list` i
`resources/read` na HTTP i stdio transportu. Klijent može da ih pročita na
`skill://sr/<naziv>/SKILL.md`. Za aktiviranje skillova u klijentu koji
podržava Agent Plugins učitajte paket iz `plugins/sr/`.
