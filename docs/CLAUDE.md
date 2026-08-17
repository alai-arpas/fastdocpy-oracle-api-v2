# fastdocpy-oracle-api-v2

Refactoring di **fastdocpy-oracle-api**: servizio dati idro-meteo ARPAS
(stazioni SASI/SAR, misure CAE, validazioni idrometriche) letto da un
database Oracle con schema poco relazionale ma alti volumi — tipico di serie
temporali di misure di sensori piuttosto che di un dominio relazionale
complesso. Storia completa delle decisioni in `docs/refactor-decisions.md`.

## Stack

- Python 3.12, gestito con `uv` (`pyproject.toml` / `uv.lock` / `.python-version`)
- FastAPI + Pydantic v2 (`pydantic-settings` per la configurazione tipizzata)
- `oracledb` in **thin mode** — nessun Oracle Instant Client richiesto, a
  differenza del progetto legacy (che installava Instant Client 19.11 via
  `alien` nel Dockerfile)
- ruff (lint/format), pytest, poethepoet (`poe`) per i task ricorrenti
- Docker/Compose a tre livelli, pattern ripreso dal progetto gemello ARPAS
  **fastdocpy-arcgis-api-v2** (stessa struttura, stesso pin Python/uv)

## Comandi principali

```bash
uv sync --locked        # installa le dipendenze
uv run poe check         # lint + format-check + test
uv run poe dev           # avvio locale con reload (http://127.0.0.1:5007)
uv run poe docker-up     # docker compose (compose.yaml + compose.secrets.yaml)
uv run poe docker-down
```

## Configurazione e segreti

Valori non sensibili in `.env` (vedi `.env.example`): `FDP_ORACLE__HOST`,
`FDP_ORACLE__PORT`, `FDP_ORACLE__SERVICE_NAME`, `FDP_ADB__DSN` (database di
destinazione per la sincronizzazione, DSN gia' pronta come nel legacy — non
componenti host/porta/service separati).

Credenziali in file singoli sotto `.secrets/` (esclusi da git e dal build
context Docker, mai in chiaro nelle env var):

```text
.secrets/FDP_ORACLE__CREDENTIALS__USER
.secrets/FDP_ORACLE__CREDENTIALS__PASSWORD
.secrets/FDP_ADB__CREDENTIALS__USER
.secrets/FDP_ADB__CREDENTIALS__PASSWORD
```

Permessi: `chmod 644` (non `600`). `compose.secrets.yaml` monta questi file
dell'host così come sono in `/run/secrets/`, preservando i permessi
dell'host — ma il container gira come utente non privilegiato `fastdocpy`
(UID/GID `10001`, vedi `Dockerfile`), diverso dall'utente host. Con `600`
(leggibile solo dal proprietario host) il processo nel container va in
`PermissionError` all'avvio, perché il suo UID non coincide con quello del
file sull'host.

Caricamento tipizzato in `app/settings.py` via `pydantic-settings`
(`BaseSettings`, prefisso env `FDP_`, delimitatore annidato `__`,
`NestedSecretsSettingsSource` per leggere i secret Docker montati in
`/run/secrets`).

## Stato del refactoring

- [x] Scheletro Docker/Compose/config: `Dockerfile`, `compose.yaml`,
      `compose.dev.yaml`, `compose.secrets.yaml`, `app/settings.py`
- [x] `app/db.py`: connessione Oracle per richiesta (dependency FastAPI
      `get_connection`, nessun pool, come nel legacy) via context manager
      `oracle_connection`
- [x] Modelli Pydantic tipizzati per le risposte in `app/models.py`
      (`Stazione`, `Trascodifica`, `MisuraCae`), sostituendo i dict
      costruiti a mano con `zip(campi, valori)` nel legacy
- [x] Porting di `/sasi`, `/sar` (`app/repositories/stazioni.py`),
      `/trascodifica` (`app/repositories/trascodifiche.py`) e
      `/misure_cae/{cod_grand}` (`app/repositories/misure_cae.py`), tutte
      con bind variables al posto delle f-string interpolate nel legacy
      (era SQL injection: `cod_grand`/`inizio`/`fine` finivano diretti nel
      testo della query)
- [x] Porting del modulo ADB (`app/repositories/adb_sync.py`, mai attivato
      in produzione nel legacy: le route erano commentate). Connessione
      distinta al database di destinazione (`AppSettings.adb`, dependency
      `get_adb_connection`) per sincronizzare MISURE_CAE e IDROMETRI_REPORT
      verso lo schema WKSP_DBPOA:
      - `GET /adb/misure_cae`: anteprima di poche righe già presenti su ADB
        (non un elenco completo), equivalente al legacy `/adb_prima`
      - `POST /adb/misure_cae/sync`, `POST /adb/idrometri_report/sync`:
        copiano l'intera tabella sorgente su ADB — erano `GET` nel legacy
        (`/adb_insert`, `/adb_insert_idro_report`), portate a `POST` perché
        mutano dati
      - lettura sorgente a blocchi (`iter_chunks`/`fetchmany`) invece di
        `cursor.fetchall()` + un unico `executemany`: risolve per questo
        percorso il rischio di saturare la memoria già segnalato più sotto
        per `IDROMETRI_REPORT`
      - `SELECT` con colonne esplicite invece di `SELECT *`: il legacy si
        affidava all'ordine fisico delle colonne per farle combaciare con
        l'insert posizionale a destinazione — fragile e silenzioso in caso
        di mismatch; ora usa gli stessi nomi già dichiarati dal legacy lato
        insert, così un disallineamento di schema fallisce in modo esplicito
- [ ] Porting delle route legacy rimanenti: validazioni idrometriche più
      ampie esposte via HTTP (oltre alla sync ADB, sopra), export CSV. Le
      route `/dati_week*`, `/pti`, `/tipo/{tipo}/{anno}/{stazione}`,
      `/bis/{numero}` nel legacy sembrano codice di prova/debug (query
      contro tabelle non documentate, scrittura di file locali) più che
      funzionalità da preservare: da confermare con l'utente prima di
      migrarle o scartarle
- [ ] `field_validator`/`model_validator` Pydantic per le regole di
      validazione dati (range plausibili, coerenza tra campi, flag di
      scarto) — i modelli attuali sono solo tipizzazione della forma dei
      dati, non ancora regole di business
- [ ] Fetch a blocchi/streaming per le risposte HTTP di lettura su tabelle
      molto grandi: le repository di lettura (`stazioni`, `trascodifiche`,
      `misure_cae`) iterano il cursore (rispettando `arraysize`) invece di
      usare `cursor.fetchall()` come il legacy, ma materializzano comunque
      l'intera lista in memoria prima di serializzarla in JSON — per
      `IDROMETRI_REPORT` esposto via HTTP (se servirà) serve ancora
      paginazione o una risposta in streaming vera e propria (la sync ADB
      sopra risolve solo il percorso lettura-sorgente/scrittura-ADB, non
      un'eventuale lettura HTTP diretta di IDROMETRI_REPORT)
- [x] Verifica connessione al DB Oracle ARPAS (sorgente) reale in thin
      mode: confermato sia in locale sia nel container, `/sar` e `/sasi`
      rispondono correttamente (nessun Instant Client necessario). Bug
      trovato e corretto durante la verifica: `compose.yaml` non aveva
      `env_file: .env` per il servizio `api` — le variabili `FDP_*` non
      sensibili non arrivavano mai al container, che ricadeva sui default
      di `OracleSettings` (`host="localhost"`) tentando di connettersi a
      se stesso (`ConnectionRefusedError`, non un problema di rete/firewall
      verso l'host Oracle reale)
- [ ] Verifica connessione al DB ADB (destinazione sync) reale: ancora da
      confermare. La DSN configurata usa `protocol=tcps` (Oracle Autonomous
      Database) senza gestione di Oracle Wallet nel codice — da confermare
      se la connessione mTLS-meno (system truststore) basta o se servirà
      aggiungere `wallet_location`

## Convenzioni

- Porta locale Docker: **5007** — coincide con quella di
  `fastdocpy-arcgis-api-v2`: non farli girare insieme in Docker sullo stesso
  host senza cambiare una delle due porte in `compose.yaml`
- Nessuna dipendenza binaria/Instant Client Oracle nel Dockerfile: solo
  `oracledb` in thin mode
- Pin Python `3.12.13-slim-bookworm` e `uv 0.4.25` allineati a
  `fastdocpy-arcgis-api-v2` (nessuna cache o runtime condiviso tra i due
  progetti, solo stessa versione per coerenza)
- Linguaggio del progetto: Python per questo servizio (dati ad alto volume,
  schema poco relazionale — poco margine per i vantaggi tipici di C#/ORM
  relazionali). Altri servizi futuri dell'organizzazione potranno essere in
  C#; vedi `docs/refactor-decisions.md` per il ragionamento completo.
