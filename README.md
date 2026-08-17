# fastdocpy-oracle-api-v2

Refactoring di **fastdocpy-oracle-api**: servizio dati idro-meteo ARPAS
(stazioni SASI/SAR, misure CAE, validazioni) letti da Oracle. Usa Python 3.12,
`uv`, FastAPI e `python-oracledb` in thin mode (nessun Instant Client
richiesto per le connessioni di base).

Le immagini Docker e la struttura di configurazione ricalcano quelle di
**fastdocpy-arcgis-api-v2**, per coerenza tra i servizi v2 ARPAS.

## Stato

`/`, `/health`, `/sasi`, `/sar`, `/trascodifica` e `/misure_cae/{cod_grand}`
portati da fastdocpy-oracle-api, con modelli Pydantic tipizzati e query con
bind variables (il legacy interpolava i parametri della request nel testo
SQL). Restano da migrare: validazioni idrometriche aggiuntive, export CSV, e
il fetch a blocchi/streaming per le tabelle molto grandi (oggi le query
restituiscono comunque l'intero result set in un'unica risposta JSON).

## Avvio

```bash
uv sync --locked
uv run poe check
uv run poe dev
```

L'API locale usa <http://127.0.0.1:5007>. Swagger UI sotto **/docs**.

## Configurazione e segreti

Valori non sensibili in `.env` (vedi `.env.example`). Credenziali Oracle in
file singoli sotto `.secrets/`:

```text
.secrets/
├── FDP_ORACLE__CREDENTIALS__USER
└── FDP_ORACLE__CREDENTIALS__PASSWORD
```

Non committare `.secrets/` (già in `.gitignore`/`.dockerignore`).

## Docker

```bash
uv run poe docker-up
uv run poe docker-down
```

Pubblicato solo su **127.0.0.1:5007** — coincide con quella di
`fastdocpy-arcgis-api-v2`: non farli girare insieme in Docker sullo stesso
host senza cambiare una delle due porte in `compose.yaml`.
