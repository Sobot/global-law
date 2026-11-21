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

Relevantni odgovori sadrže `trailers` (izvorni ključevi i prve vrednosti), `trailers_all` (sve vrednosti, uključujući ponovljene), `commit_url` i `file_url` kada odgovarajući MD fajl postoji u commitu. `file_url` u rezultatima pretrage bez datuma pokazuje na pin korpusa, ne na pojedinačnu izmenu. `In-force` je pravni datum, a ne datum Git commita. Zvanične reference su i dalje deo odgovora.

## CI/CD

Workflow `serbia.yml` testira i objavljuje image u GHCR. Na rasporedu osvežava samo pin srpskog korpusa. Na grani `main` deployment koristi namenski AWS OIDC role (bez statičkih AWS ključeva), Systems Manager i skriptu `tools/deploy_serbia_test.sh`. Ako GHCR zahteva autentikaciju, isti source i corpus pin se izgrade na instanci. Kontejner sluša samo na lokalnom portu 8080 instance; nginx i CloudFront omogućavaju HTTPS.

## Test

```sh
python -m unittest discover -s tests -p test_serbia_refs.py -v
```

Testovi koriste stvarnu izmenu ZKP-a iz Sl. glasnika RS 35/2019.
