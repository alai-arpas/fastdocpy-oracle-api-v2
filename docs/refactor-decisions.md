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

## 5. Prima ondata di porting: SASI/SAR, trascodifiche, misure CAE

Portate `/sasi`, `/sar`, `/trascodifica` e `/misure_cae/{cod_grand}`, con
tre scelte deliberate rispetto al comportamento legacy:

- **Bind variables sempre**, mai SQL costruito con f-string sui parametri
  della request. Il legacy interpolava direttamente `cod_grand`, `inizio` e
  `fine` nel testo della query (`query_idro_valida.py`): SQL injection
  concreta, dato che questi valori arrivano dalla request HTTP. `oracledb`
  supporta i bind sia per stringhe che per `datetime` Python legati a
  colonne DATE/TIMESTAMP.
- **Date come `datetime` ISO 8601 nei query param**, non più stringhe nel
  formato `dd-mm-yyyy hh24:mi` da interpretare con `to_date()` lato SQL.
  FastAPI valida/converte da solo; è una modifica di contratto verso i
  consumer di `/misure_cae/{cod_grand}` (che dovranno passare es.
  `2022-11-15T03:00:00` invece di `15-11-2022 03:00`), accettata perché
  siamo comunque in un servizio v2 con URL/contratto non ancora esposto a
  consumer esterni.
- **Non ancora streaming/paginazione**: le repository iterano il cursore
  (rispettando `arraysize`) invece di `cursor.fetchall()`, il che evita un
  doppio round-trip in memoria lato driver, ma il risultato viene comunque
  accumulato in una lista Python prima di essere serializzato in JSON.
  Per tabelle molto grandi (`IDROMETRI_REPORT`) resta da fare un vero
  streaming o paginazione: rimane un punto aperto in `docs/CLAUDE.md`.

Non ancora portate: `/dati_week`, `/dati_week_campi`, `/pti`,
`/tipo/{tipo}/{anno}/{stazione}`, `/bis/{numero}`. Nel legacy hanno tutti
tratti da codice di prova (tabelle come `GIS_PROVA_1_WEEK`, scrittura di
CSV su filesystem locale, endpoint numerati senza logica di dominio chiara)
più che funzionalità di prodotto — da confermare con l'utente se vadano
migrate o scartate prima di procedere oltre.

## 6. Porting del modulo ADB (sincronizzazione verso WKSP_DBPOA)

Il legacy conteneva un secondo modulo, `app/adb/` (`conn_env.py`,
`query.py`), per copiare dati dal database Oracle sorgente ARPAS a un
secondo database Oracle di destinazione ("ADB"), schema `WKSP_DBPOA`:
`MISURE_CAE` e `IDROMETRI_REPORT` lette per intero dalla sorgente e
inserite nel target. **Codice mai attivato in produzione**: sia le tre
route in `main.py` (`/adb_prima`, `/adb_insert`, `/adb_insert_idro_report`)
sia l'intero contenuto di `app/adb/conn_env.py` e `app/adb/query.py` erano
racchiusi in una docstring/commento, quindi disattivi. Portato su richiesta
esplicita dell'utente, con tre correzioni deliberate rispetto
all'originale:

- **Connessione via DSN grezza, non host/porta/service_name**: il legacy
  passava a `oracledb.connect()` una DSN già pronta
  (`SASSAPI_ADB_dns`), diversamente dalla connessione sorgente che
  componeva `host:port/service_name`. La nuova `AdbSettings` (config
  `FDP_ADB__DSN`) mantiene la stessa forma, perché non c'è modo di sapere
  dal codice legacy se quella DSN sia un semplice `host:port/service`, un
  alias TNS, o un connect descriptor Easy Connect Plus con opzioni
  aggiuntive — comporla da componenti separate avrebbe richiesto
  un'assunzione non verificabile. Nessuna gestione di Oracle Wallet è stata
  aggiunta: il legacy non ne aveva, quindi non ne aggiungiamo senza
  conferma che serva davvero (se ADB risultasse essere un Autonomous
  Database Oracle Cloud con mTLS obbligatorio, servirebbe rivedere questo
  punto).
- **Lettura sorgente a blocchi invece di `fetchall()` + un unico
  `executemany`**: stesso rischio di saturare la memoria già segnalato per
  `IDROMETRI_REPORT` nella sezione 1, qui concreto perché è proprio una
  delle tabelle copiate per intero, senza filtri. La nuova
  `app.db.iter_chunks` legge con `cursor.fetchmany(ARRAY_SIZE)` a
  ripetizione e inserisce un blocco alla volta con `executemany`,
  mantenendo un solo commit finale (stessa semantica transazionale
  "tutto o niente" dell'originale, ma senza mai avere l'intera tabella in
  memoria Python contemporaneamente).
- **SELECT con colonne esplicite invece di `SELECT *`**: il legacy leggeva
  `SELECT * FROM MISURE_CAE`/`IDROMETRI_REPORT` e passava le tuple
  risultanti a un insert posizionale (`:0, :1, ...`), contando sul fatto
  che l'ordine fisico delle colonne della tabella sorgente combaciasse con
  l'ordine dei parametri dell'insert — un accoppiamento implicito e
  silenzioso: se lo schema cambia, i dati finiscono nella colonna sbagliata
  senza errori. La query sorgente elenca ora esplicitamente le stesse
  colonne già dichiarate dal legacy lato insert (`COD_STAZ, COD_GRAND,
  DATA_MIS, VALORE, COD_VALID, PERIODO_ARC, ORA, MINUTO` per MISURE_CAE;
  analogo per IDROMETRI_REPORT): stesso comportamento se lo schema è quello
  atteso dal legacy, ma un mismatch di schema fa fallire la query invece di
  corrompere silenziosamente i dati copiati.

Le due route che scrivono (`/adb_insert`, `/adb_insert_idro_report`) erano
`GET` nel legacy; portate a `POST` (`/adb/misure_cae/sync`,
`/adb/idrometri_report/sync`) perché mutano dati sul database di
destinazione — semantica HTTP corretta, non solo pignoleria: un `GET`
rifetchato da un proxy/browser/crawler potrebbe altrimenti innescare
inserimenti non voluti.

## 7. MISURE_CAE non è una tabella sola: scope temporaneo su MISURE_CAE_OLD

Verificando la connessione reale (sezione precedente sullo stato del
refactoring in `docs/CLAUDE.md`), è emerso che `MISURE_CAE` sul database
ARPAS/SASSARI è in realtà una famiglia di tabelle partizionate a mano per
periodo — non solo la tabella `MISURE_CAE` usata finora dal codice:

- `MISURE_CAE`: dati correnti, in pratica solo gli ultimi giorni (~12
  giorni osservati il 17 agosto 2026, non i "due mesi" ipotizzati
  inizialmente)
- `MISURE_CAE_OLD`: dal 2022-01-01 al 2025-11-15 osservato
- `MISURE_CAE_2017` … `MISURE_CAE_2021`: un anno ciascuna
- `MISURE_CAE_05_20`: 2005–2020, ma con un conteggio righe troppo basso per
  essere un duplicato pieno delle tabelle annuali che si sovrappongono
  (66-71M righe/anno da sole contro 31M in totale su 16 anni) — probabile
  sottoinsieme, non confermato
- un **buco di copertura** di circa 8 mesi e mezzo tra la fine di
  `MISURE_CAE_OLD` (2025-11-15) e l'inizio di `MISURE_CAE` (2026-08-05), non
  ancora spiegato

C'è inoltre un **secondo database Oracle**, schema `CAE` (diverso da
`ARPAS`), con una propria `MISURE_CAE_OLD` quasi identica ma con una
colonna in più (`COD_CP`) e altre tabelle non ancora esplorate
(`MISURE_CAE_EXTRA`, `MISURE_CAE_MAMOIADA_PCT`) — relazione con il database
ARPAS/SASSARI non ancora chiarita.

Decisione: finché questi punti non sono chiariti, **si legge solo da
`MISURE_CAE_OLD` sul database ARPAS/SASSARI già configurato**
(`FDP_ORACLE__*`) — non da `MISURE_CAE`, dalle tabelle annuali, da
`MISURE_CAE_05_20`, né dal database con schema `CAE`. Cambiato in
`app/repositories/misure_cae.py` (`fetch_misure_cae`, usata da
`GET /misure_cae/{cod_grand}`) e `app/repositories/adb_sync.py`
(`sync_misure_cae`, usata da `POST /adb/misure_cae/sync`) — la tabella di
destinazione su ADB resta `wksp_dbpoa.misure_cae`, cambia solo la sorgente.
Questo è uno scope provvisorio: quando i punti sopra saranno chiariti, la
logica di selezione tabella andrà rivista (verosimilmente una selezione
per anno, sul modello di `oratabss/tabelle.py` nel legacy).

## 8. Catalogo reale dei COD_GRAND in MISURE_CAE_OLD

L'utente ha estratto ed esportato in `app/data/misure_cae_old.csv` una query di
aggregazione `COD_STAZ, COD_GRAND, COUNT(*), MIN(DATA_MIS), MAX(DATA_MIS)`
su `ARPAS.MISURE_CAE_OLD` (1054 combinazioni stazione×grandezza). Questo dà
per la prima volta un quadro confermato di cosa contiene davvero la
tabella, invece di ipotesi basate su pochi campioni:

- **163 COD_STAZ distinti** (non ~200 come stimato inizialmente)
- **27 COD_GRAND distinti** (non ~15 come stimato inizialmente — quasi il
  doppio)
- `PCT` domina nettamente il volume (oltre 258 milioni di righe su 132
  stazioni) — è quasi certamente il codice pioggia, e spiega perché una
  query di un solo giorno senza filtro stazione può restituire centinaia
  di migliaia di righe (visto in pratica: 185.889 righe per un giorno di
  `PCT` su tutte le stazioni)
- il commento del legacy (`P1H = pioggia`) è **sbagliato o relativo a
  un'altra tabella**: `P1H` non compare tra i 27 codici realmente presenti
  in `MISURE_CAE_OLD`. `TCI`, `LIT`, `LJT` invece combaciano con la
  spiegazione legacy (temperatura, livello primo/secondo idrometro)
- molti codici minori sembrano varianti statistiche di una stessa
  grandezza base (es. `TCI`/`TCM`/`TCL`/`TCH`, `UCI`/`UCH`/`UCL`) — non
  confermato, servirebbe la tabella `GRANDEZZE` (vista ma non ancora
  esplorata, sezione 6 della checklist in `docs/CLAUDE.md`) per le
  descrizioni ufficiali

Aggiornati di conseguenza i commenti in `app/main.py` (route
`GET /misure_cae/{cod_grand}`) e la documentazione inline di
`GET /html/misure_cae` (`app/views.py`), che ora citano l'elenco
confermato invece di pochi esempi e rimandano al CSV per il dettaglio
completo per stazione.

Il CSV vive sotto `app/data/`, non `docs/`: `docs/` è escluso dal build
context Docker (`.dockerignore`), quindi un file letto a runtime da lì
avrebbe funzionato in locale ma non nel container — scoperto e corretto
prima di costruirci sopra `app/catalogo_misure.py` (vedi sotto).

### Catalogo caricato all'avvio, select filtrabili

Su richiesta dell'utente, il CSV viene caricato **una volta all'avvio**
(`app.catalogo_misure.get_catalogo`, `@lru_cache`, salvato in
`application.state.catalogo`) invece che ad ogni richiesta — non e' la
fonte di verita' (resta il database), e se il file manca il catalogo
risulta vuoto senza bloccare l'avvio (dato accessorio per l'interfaccia).

Aggiunte di conseguenza:

- `GET /misure_cae/catalogo` (JSON) e `GET /html/misure_cae/catalogo`
  (pagina HTML) — registrata **prima** di `/misure_cae/{cod_grand}`
  nell'ordine delle route, altrimenti quest'ultima intercetterebbe
  "catalogo" come se fosse un valore di `cod_grand`
- il form di `GET /html/misure_cae` usa ora `<select>` per `cod_grand`/
  `cod_staz` invece di campi di testo libero, popolate dal catalogo
- un filtro "tipo Excel" (`app.html.render_filterable_table`) sulle
  tabelle della pagina catalogo: casella di ricerca che nasconde dal vivo
  le righe non corrispondenti, lato client, senza round-trip al server
  (adatto alle ~1000 righe della tabella di dettaglio, non a result set
  enormi non paginati)
