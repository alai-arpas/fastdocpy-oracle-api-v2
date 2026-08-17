# Architettura — modello C4

Documentazione architetturale di **fastdocpy-oracle-api-v2** secondo il
[modello C4](https://c4model.com/): quattro livelli di dettaglio crescente
(Contesto, Container, Componenti, Codice — quest'ultimo omesso, il codice
stesso ne fa le veci), più le **viste dinamiche** per i flussi a runtime.
I diagrammi sono in Mermaid (renderizzati nativamente da GitHub); lo stile
richiama la notazione C4 (persona/sistema/container/componente) senza usare
la sintassi sperimentale `C4Context`/`C4Container` di Mermaid, per garantire
un rendering affidabile ovunque.

## Livello 1 — Contesto

Chi usa il sistema e con quali sistemi esterni comunica.

```mermaid
flowchart TD
    user["👤 Operatore/consumer ARPAS<br/>(persona)<br/>Consulta stazioni, misure e trascodifiche<br/>via browser (pagine HTML) o client HTTP (JSON)"]
    system["📦 fastdocpy-oracle-api-v2<br/>(sistema software)<br/>Espone i dati idro-meteo ARPAS<br/>via API JSON e pagine HTML"]
    oracleSrc["🗄️ Oracle ARPAS<br/>(sistema esterno, sorgente)<br/>STAZIONI, MISURE_CAE,<br/>TRANSCODIFICHE_CAE_ARPAS, ..."]
    oracleAdb["🗄️ Oracle ADB — WKSP_DBPOA<br/>(sistema esterno, destinazione)<br/>Copia sincronizzata di MISURE_CAE<br/>e IDROMETRI_REPORT"]

    user -->|"HTTPS: naviga pagine HTML,<br/>chiama endpoint JSON"| system
    system -->|"legge (oracledb thin mode,<br/>bind variables)"| oracleSrc
    system -->|"scrive (sync a blocchi:<br/>fetchmany + executemany + commit)"| oracleAdb
```

## Livello 2 — Container

Il sistema è oggi un solo container applicativo (nessun database proprio:
legge/scrive solo sui due Oracle esterni).

```mermaid
flowchart TD
    user["👤 Client HTTP<br/>(browser o script)"]

    subgraph boundary["fastdocpy-oracle-api-v2"]
        api["🐳 api<br/>(container Docker)<br/>Python 3.12 + FastAPI + Uvicorn<br/>porta 8000 (127.0.0.1:5007 sull'host)<br/>utente non privilegiato fastdocpy (UID 10001)"]
    end

    oracleSrc["🗄️ Oracle ARPAS<br/>host:porta/service_name<br/>(FDP_ORACLE__*)"]
    oracleAdb["🗄️ Oracle ADB<br/>DSN TCPS, senza wallet<br/>(FDP_ADB__*)"]

    user -->|"HTTP"| api
    api -->|"oracledb thin,<br/>una connessione per richiesta"| oracleSrc
    api -->|"oracledb thin,<br/>una connessione per richiesta"| oracleAdb
```

Configurazione (`app/settings.py`, `pydantic-settings`): valori non
sensibili da `.env`, credenziali da file singoli in `.secrets/` (dev) o
Docker secrets in `/run/secrets` (container) — mai in chiaro nelle env var.

## Livello 3 — Componenti

Struttura interna del container `api`.

```mermaid
flowchart TD
    subgraph api["Container: api (processo FastAPI/Uvicorn)"]
        main["main.py<br/>«boundary»<br/>Route HTTP, dependency injection<br/>delle connessioni Oracle per richiesta"]
        settings["settings.py<br/>«config»<br/>AppSettings / OracleSettings / AdbSettings<br/>(pydantic-settings)"]
        db["db.py<br/>«infrastruttura dati»<br/>oracle_connection, new_cursor,<br/>iter_chunks (lettura a blocchi)"]
        models["models.py<br/>«modelli risposta»<br/>Stazione, Trascodifica, MisuraCae"]
        reposRead["repositories/<br/>stazioni.py · trascodifiche.py<br/>misure_cae.py<br/>«lettura, bind variables»"]
        reposAdb["repositories/adb_sync.py<br/>«ETL sorgente → ADB»<br/>lettura e scrittura a blocchi"]
        home["home.py<br/>«vista»<br/>Home page: elenca le route<br/>registrate su FastAPI (auto-scoperta)"]
        html["html.py<br/>«vista, condiviso»<br/>Shell HTML (Pico.css) + tabelle"]
        views["views.py<br/>«vista»<br/>Pagine HTML sopra i dati<br/>(es. /html/trascodifica)"]
    end

    main --> settings
    main --> db
    main --> reposRead
    main --> reposAdb
    main --> home
    main --> views
    reposRead --> models
    reposRead --> db
    reposAdb --> db
    home --> html
    views --> html
```

## Modello dati (risposte Pydantic)

```mermaid
classDiagram
    class Stazione {
      +str cod_staz
      +str nome
    }
    class Trascodifica {
      +str stazione
      +str cod_staz_cae
      +str cod_staz_arpa
    }
    class MisuraCae {
      +str cod_staz «max 9»
      +str cod_grand «max 3»
      +float valore?
      +str cod_valid? «max 1»
      +datetime data
    }
```

I vincoli di lunghezza di `MisuraCae` sono allineati al DDL reale di
`MISURE_CAE` (`docs/refactor-decisions.md`, sezione 5). Tutti i modelli
sono `frozen=True`: immutabili una volta costruiti.

## Flussi (viste dinamiche)

### Lettura semplice — `GET /sar`

```mermaid
sequenceDiagram
    participant C as Client
    participant M as main.py (route /sar)
    participant DEP as get_connection (dependency)
    participant DB as db.py (oracle_connection)
    participant ORA as Oracle ARPAS
    participant R as repositories/stazioni.py

    C->>M: GET /sar
    M->>DEP: richiede la connessione
    DEP->>DB: oracle_connection(dsn, credentials)
    DB->>ORA: oracledb.connect() (thin mode)
    ORA-->>DB: connessione aperta
    DB-->>DEP: yield connection
    DEP-->>M: connection
    M->>R: fetch_stazioni_sar(connection)
    R->>ORA: SELECT ... WHERE tipo_staz = :tipo_staz
    ORA-->>R: righe
    R-->>M: list[Stazione]
    M-->>C: 200 JSON
    M->>DB: fine richiesta: connection.close()
```

### Lettura con parametri e bind variables — `GET /misure_cae/{cod_grand}`

```mermaid
sequenceDiagram
    participant C as Client
    participant M as main.py (route /misure_cae/{cod_grand})
    participant R as repositories/misure_cae.py
    participant ORA as Oracle ARPAS

    C->>M: GET /misure_cae/P1H?inizio=...&fine=...
    M->>M: FastAPI valida cod_grand, inizio, fine (datetime ISO 8601)
    M->>R: fetch_misure_cae(connection, cod_grand, inizio, fine)
    R->>ORA: SELECT ... WHERE cod_grand=:cod_grand<br/>AND data_mis BETWEEN :inizio AND :fine
    Note over R,ORA: bind variables, non interpolazione SQL<br/>(era SQL injection nel legacy)
    ORA-->>R: righe
    R-->>M: list[MisuraCae]
    M-->>C: 200 JSON
```

### Sincronizzazione ADB a blocchi — `POST /adb/misure_cae/sync`

```mermaid
sequenceDiagram
    participant C as Client
    participant M as main.py (route .../sync)
    participant SRC as Oracle ARPAS (sorgente)
    participant A as repositories/adb_sync.py
    participant ADB as Oracle ADB (WKSP_DBPOA)

    C->>M: POST /adb/misure_cae/sync
    M->>A: sync_misure_cae(source_connection, adb_connection)
    A->>SRC: SELECT colonne esplicite FROM misure_cae
    loop per ogni blocco (fetchmany, ARRAY_SIZE righe)
        A->>SRC: fetchmany(300)
        SRC-->>A: blocco di righe
        A->>ADB: executemany(INSERT ..., blocco)
    end
    A->>ADB: commit()
    A-->>M: numero righe inserite
    M-->>C: 200 JSON {"inseriti": N}
```

Nessun `cursor.fetchall()`: la tabella sorgente non viene mai
materializzata per intero in memoria (vedi `docs/refactor-decisions.md`,
sezione 6).

### Home page auto-generata — `GET /`

```mermaid
sequenceDiagram
    participant C as Browser
    participant M as main.py (route /)
    participant H as home.py (render_home)
    participant HTML as html.py (page_shell)

    C->>M: GET /
    M->>H: render_home(application)
    H->>H: itera application.routes,<br/>raggruppa per tag (system, html, stazioni, ...)
    H->>HTML: page_shell(titolo, descrizione, sezioni)
    HTML-->>H: documento HTML (Pico.css)
    H-->>M: HTML
    M-->>C: 200 text/html
```

La home page non ha un elenco di route scritto a mano: viene ricostruita
leggendo `application.routes` ad ogni richiesta, quindi resta corretta da
sola quando si aggiungono o si tolgono endpoint (vedi `app/home.py`).

## Da tenere aggiornato

Questo documento va rivisto quando cambia la struttura, non ad ogni singola
route aggiunta:

- nuovo **container** (es. un secondo servizio, un database applicativo
  proprio) → aggiorna Livello 1 e 2
- nuovo **modulo** in `app/` con una responsabilità distinta → aggiorna
  Livello 3
- nuovo **flusso** con una forma diversa da quelli già documentati (es. una
  vera risposta in streaming, un webhook, un job schedulato) → aggiungi un
  diagramma di sequenza
