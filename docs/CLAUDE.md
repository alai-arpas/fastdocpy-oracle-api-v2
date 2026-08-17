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
`FDP_ORACLE__PORT`, `FDP_ORACLE__SERVICE_NAME`.

Credenziali in file singoli sotto `.secrets/` (esclusi da git e dal build
context Docker, mai in chiaro nelle env var):

```text
.secrets/FDP_ORACLE__CREDENTIALS__USER
.secrets/FDP_ORACLE__CREDENTIALS__PASSWORD
```

Caricamento tipizzato in `app/settings.py` via `pydantic-settings`
(`BaseSettings`, prefisso env `FDP_`, delimitatore annidato `__`,
`NestedSecretsSettingsSource` per leggere i secret Docker montati in
`/run/secrets`).

## Stato del refactoring

- [x] Scheletro Docker/Compose/config: `Dockerfile`, `compose.yaml`,
      `compose.dev.yaml`, `compose.secrets.yaml`, `app/settings.py`,
      `app/main.py` minimale con solo `/` e `/health`
- [ ] Porting delle route legacy: misure CAE (`/misure_cae/{cod_grand}`),
      stazioni SASI/SAR (`/sasi`, `/sar`), validazioni idrometriche,
      trascodifiche CAE↔ARPAS, export CSV
- [ ] Modelli Pydantic tipizzati per le risposte (sostituendo i dict
      costruiti a mano con `zip(campi, valori)` nel legacy) — valutare
      `field_validator`/`model_validator` per le regole di validazione dati
- [ ] Fetch a blocchi/streaming invece di `cursor.fetchall()` senza limiti:
      nel legacy alcune query (es. su `IDROMETRI_REPORT`) non hanno alcun
      filtro/limite e su tabelle grandi rischiano di saturare la memoria
- [ ] Verifica che `oracledb` thin mode si connetta correttamente al DB
      Oracle ARPAS reale (nessun Instant Client nel Dockerfile v2: da
      confermare prima di considerarlo definitivo)

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
