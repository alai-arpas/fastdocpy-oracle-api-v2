# fastdocpy-oracle-api-v2

Refactoring di **fastdocpy-oracle-api**: servizio dati idro-meteo ARPAS
(stazioni SASI/SAR, misure CAE, validazioni) letti da Oracle. Usa Python 3.12,
`uv`, FastAPI e `python-oracledb` in thin mode (nessun Instant Client
richiesto per le connessioni di base).

Le immagini Docker e la struttura di configurazione ricalcano quelle di
**fastdocpy-arcgis-api-v2**, per coerenza tra i servizi v2 ARPAS.

## Stato

Scheletro iniziale: solo `/` e `/health`. Le route legacy (misure, stazioni,
validazioni CAE) vanno migrate progressivamente da fastdocpy-oracle-api,
sostituendo `cursor.fetchall()` senza limiti con fetch a blocchi/streaming e
introducendo modelli Pydantic tipizzati per le risposte.

## Avvio

```powershell
uv sync --locked
uv run poe check
uv run poe dev
```

L'API locale usa <http://127.0.0.1:5008>. Swagger UI sotto **/docs**.

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

```powershell
uv run poe docker-up
uv run poe docker-down
```

Pubblicato solo su **127.0.0.1:5008** (fastdocpy-arcgis-api-v2 usa già 5007
in locale: porta diversa per evitare collisioni se girano insieme).
