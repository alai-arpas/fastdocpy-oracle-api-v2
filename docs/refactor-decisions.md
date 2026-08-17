# Log delle decisioni — refactoring fastdocpy-oracle-api-v2

Sintesi delle decisioni prese durante l'avvio del refactoring di
**fastdocpy-oracle-api** (servizio Python/FastAPI dati idro-meteo ARPAS su
Oracle) in questo progetto v2. Aggiornato al 17 agosto 2026.

## 1. Il sistema legacy

`fastdocpy-oracle-api` (repo separato, github `alai-arpas/fastdocpy-oracle-api`)
è un servizio FastAPI piccolo: una decina di endpoint che leggono dati
idro-meteo da Oracle (stazioni SASI/SAR, misure CAE, validazioni, tabelle
STAZIONI/UBICAZIONI), quasi tutti in sola lettura, con query SQL scritte a
mano via cursori (`oracledb`, senza ORM) e qualche export CSV con pandas.
Deploy come container Docker dietro Traefik, mantenuto da un solo
sviluppatore.

Il Dockerfile legacy installa l'Oracle Instant Client 19.11 convertendo
l'rpm con `alien` — un passaggio fragile. Il progetto usa già `oracledb`
(driver moderno, ex cx_Oracle), che dalla versione 1.0 supporta il **thin
mode** senza alcun client nativo per connessioni di base: l'Instant Client
nel Dockerfile legacy è quasi certamente superfluo.

Nota tecnica di rischio: il codice legacy usa quasi ovunque
`cursor.fetchall()` senza limiti espliciti (es. `IDROMETRI_REPORT` letta per
intero), il che su tabelle con **molti dati** può causare problemi di
memoria — da correggere in v2 con fetch a blocchi o risposte in streaming,
indipendentemente dal linguaggio.

## 2. Python vs C#, in ottica microservizi

La domanda iniziale ("Python o C# per il refactoring?") si è evoluta:
l'obiettivo non è scegliere un linguaggio unico, ma capire come dividerli
bene in un'architettura a microservizi, dato che entrambi verranno usati in
futuro.

Criterio emerso: la scelta è per-servizio, guidata da cosa fa il servizio,
non da quale linguaggio "vince" in assoluto. Il dato Oracle di questo
progetto ha **tabelle con pochissime relazioni ma molti dati** — tipico di
serie temporali/misure di sensori. Questo pesa sulla scelta in due modi:

- Con schema poco relazionale, l'ORM/tipizzazione relazionale di C# (es.
  Entity Framework) perde gran parte del vantaggio tradizionale: non c'è un
  grafo di relazioni complesso da modellare.
- Il fattore che conta davvero è la gestione efficiente di grandi result
  set (fetch a blocchi/streaming), non la modellazione del dominio — un
  problema comune a entrambi i linguaggi, non risolto meglio dall'uno o
  dall'altro di per sé.

Per questo, per un servizio che espone dati grezzi/aggregati da tabelle
piatte molto grandi, **Python resta la scelta più naturale**: più veloce da
scrivere, nessuna complessità di dominio da far valere con la tipizzazione
forte.

C# comincerebbe a valere la pena per servizi futuri con logica applicativa
più pesante sopra i dati grezzi — regole di business, calcolo di indicatori
derivati, alerting, orchestrazione tra più fonti — dove "cosa fa il
servizio" conta più di "quanti dati sposta". Non ancora chiarito: quali
altri servizi/domini sono previsti oltre a questa API Oracle, se ci sarà
logica di validazione/business più ricca a valle, se c'è già investimento
.NET altrove nell'organizzazione ARPAS.

### Pydantic come livello di validazione

Pydantic (già dipendenza di FastAPI, presente ma inutilizzata nel legacy)
copre in Python buona parte del bisogno di "validazione/regole di business"
ipotizzato sopra: modelli tipizzati per le risposte (sostituendo i dict
costruiti a mano con `zip(campi, valori)`) e validator (`field_validator`,
`model_validator`) per esprimere le regole di validazione delle misure
(range plausibili, coerenza tra campi, flag di scarto). Questo riduce
ulteriormente l'argomento per spostare quella logica su un servizio C# a
parte. Da usare Pydantic v2 (non v1 come nel legacy) per le prestazioni sui
volumi alti — core riscritto in Rust, e validazione a blocchi/`TypeAdapter`
invece che riga per riga se i result set diventano molto grandi.

## 3. Scheletro Docker/config

Su richiesta esplicita, lo scheletro Docker/Compose/configurazione di questo
progetto riusa il pattern del progetto gemello ARPAS
**fastdocpy-arcgis-api-v2** (stesso ente, stesso stile di refactoring v2):

- Python 3.12 + `uv` (`pyproject.toml`/`uv.lock`/`.python-version`), ruff,
  pytest, poethepoet
- Dockerfile non-root (utente `fastdocpy` uid/gid 10001), healthcheck su
  `/health`, pin `python:3.12.13-slim-bookworm` e `uv 0.4.25` allineati
  (stessa versione, non cache/runtime condivisi)
- Tre file compose: `compose.yaml` (base, porta pubblicata solo su
  `127.0.0.1`), `compose.dev.yaml` (hot reload via `develop.watch`),
  `compose.secrets.yaml` (Docker secrets da file in `.secrets/`, non env var
  in chiaro)
- Configurazione tipizzata con `pydantic-settings`: prefisso env `FDP_`,
  delimitatore annidato `__`, `NestedSecretsSettingsSource` per i secret
  Docker annidati (es. `FDP_ORACLE__CREDENTIALS__USER`)

Adattamenti specifici Oracle rispetto al modello ArcGIS: nessun Instant
Client nel Dockerfile (thin mode `oracledb`); convenzione
`FDP_ORACLE__HOST/PORT/SERVICE_NAME` (non sensibili) e
`FDP_ORACLE__CREDENTIALS__USER/PASSWORD` (secret).

Porta locale: inizialmente assegnata **5008** per evitare la collisione con
`fastdocpy-arcgis-api-v2` (che usa 5007). Successivamente riportata a
**5007** su richiesta: i due servizi condividono quindi la stessa porta
locale e non possono girare insieme in Docker sullo stesso host senza
modificarla di nuovo in `compose.yaml`.

`app/main.py` resta volutamente uno scheletro con solo `/` e `/health`: le
route legacy vanno ancora migrate (vedi checklist in `CLAUDE.md`).

## 4. Ambiente di sviluppo: passaggio a WSL

Lo sviluppo si è spostato da Windows nativo
(`C:\Users\alai\source\repos\fastdocpy-oracle-api-v2`, non più usata) a WSL
(Ubuntu 26.04), con repo clonato in `~/aprj/fastdocpy-oracle-api-v2` e
autenticazione git via SSH (utente/org GitHub `alai-arpas`). Motivazione
tecnica: il filesystem Windows montato in WSL (`/mnt/c/...`) ha notifiche di
modifica file lente/inaffidabili, il che avrebbe reso poco affidabile
l'hot-reload di `compose.dev.yaml` (`develop.watch`); il filesystem nativo
Linux di WSL non ha questo limite.

Per lo sviluppo dentro WSL sono supportati sia Claude Code CLI (installato
direttamente dentro la distro, non su Windows) sia l'estensione VS Code
tramite "Remote - WSL", oltre all'app desktop Claude Code con supporto
dedicato a sessioni WSL2.
