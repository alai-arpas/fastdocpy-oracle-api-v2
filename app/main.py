"""Boundary FastAPI del servizio Oracle idro-meteo.

Le route aprono una connessione Oracle per richiesta tramite la dependency
`get_connection` (stesso schema del legacy: nessun pool), ma passano sempre
i parametri come bind variables invece di interpolarli nel testo SQL.
"""

from collections.abc import Iterator
from datetime import datetime
from typing import Annotated

import oracledb
from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.db import oracle_connection
from app.home import render_home
from app.models import MisuraCae, Stazione, Trascodifica
from app.repositories import adb_sync as adb_sync_repo
from app.repositories import misure_cae as misure_cae_repo
from app.repositories import stazioni as stazioni_repo
from app.repositories import trascodifiche as trascodifiche_repo
from app.settings import AppSettings, get_settings


class HealthResponse(BaseModel):
    status: str
    service: str


class SyncResult(BaseModel):
    inseriti: int


def get_connection(request: Request) -> Iterator[oracledb.Connection]:
    """Connessione Oracle al database sorgente ARPAS per la durata della richiesta."""

    settings: AppSettings = request.app.state.settings
    with oracle_connection(
        dsn=settings.oracle.dsn, credentials=settings.oracle.credentials
    ) as connection:
        yield connection


def get_adb_connection(request: Request) -> Iterator[oracledb.Connection]:
    """Connessione Oracle al database di destinazione ADB per la richiesta."""

    settings: AppSettings = request.app.state.settings
    with oracle_connection(
        dsn=settings.adb.dsn, credentials=settings.adb.credentials
    ) as connection:
        yield connection


OracleConnection = Annotated[oracledb.Connection, Depends(get_connection)]
AdbConnection = Annotated[oracledb.Connection, Depends(get_adb_connection)]


def create_app(settings: AppSettings | None = None) -> FastAPI:
    """Compone l'app senza aprire connessioni Oracle all'import."""

    runtime_settings = settings or get_settings()

    application = FastAPI(
        title="fastdocpy Oracle API v2",
        description="Refactoring del servizio dati idro-meteo ARPAS su Oracle.",
        version="0.1.0",
    )
    application.state.settings = runtime_settings

    @application.get("/", response_class=HTMLResponse, tags=["system"])
    def read_root() -> HTMLResponse:
        """Pagina di benvenuto con i collegamenti alle API disponibili."""

        return HTMLResponse(render_home(application))

    @application.get("/health", response_model=HealthResponse, tags=["system"])
    def health() -> HealthResponse:
        """Liveness del processo, senza verificare la raggiungibilita' di Oracle."""

        return HealthResponse(status="ok", service="fastdocpy-oracle-api-v2")

    @application.get("/sasi", response_model=list[Stazione], tags=["stazioni"])
    def sasi(connection: OracleConnection) -> list[Stazione]:
        """Stazioni di tipo SASI (rete MTX)."""

        return stazioni_repo.fetch_stazioni_sasi(connection)

    @application.get("/sar", response_model=list[Stazione], tags=["stazioni"])
    def sar(connection: OracleConnection) -> list[Stazione]:
        """Stazioni di tipo SAR."""

        return stazioni_repo.fetch_stazioni_sar(connection)

    @application.get(
        "/trascodifica", response_model=list[Trascodifica], tags=["trascodifiche"]
    )
    def trascodifica(connection: OracleConnection) -> list[Trascodifica]:
        """Corrispondenza stazioni CAE <-> ARPAS."""

        return trascodifiche_repo.fetch_trascodifiche_cae(connection)

    @application.get(
        "/misure_cae/{cod_grand}", response_model=list[MisuraCae], tags=["misure"]
    )
    def misure_cae(
        cod_grand: str,
        inizio: datetime,
        fine: datetime,
        connection: OracleConnection,
    ) -> list[MisuraCae]:
        """Misure di validazione CAE per grandezza e intervallo di date.

        `cod_grand`: P1H = pioggia, TCI = temperatura, LIT/LJT = livello
        primo/secondo idrometro. `inizio`/`fine` sono datetime ISO 8601
        (es. `2022-11-15T03:00:00`); a differenza del legacy non serve piu'
        il formato `dd-mm-yyyy hh24:mi`, la conversione la fa FastAPI.
        """

        return misure_cae_repo.fetch_misure_cae(
            connection, cod_grand=cod_grand, inizio=inizio, fine=fine
        )

    @application.get("/adb/misure_cae", tags=["adb"])
    def adb_misure_cae_sample(
        connection: AdbConnection, limite: int = 8
    ) -> list[tuple]:
        """Anteprima di poche righe gia' presenti su ADB, per verifica manuale
        (non un elenco completo della tabella).
        """

        return adb_sync_repo.fetch_misure_cae_adb_sample(connection, quante=limite)

    @application.post("/adb/misure_cae/sync", response_model=SyncResult, tags=["adb"])
    def adb_misure_cae_sync(source: OracleConnection, adb: AdbConnection) -> SyncResult:
        """Copia l'intera MISURE_CAE dal database sorgente ad ADB (WKSP_DBPOA)."""

        inseriti = adb_sync_repo.sync_misure_cae(source, adb)
        return SyncResult(inseriti=inseriti)

    @application.post(
        "/adb/idrometri_report/sync", response_model=SyncResult, tags=["adb"]
    )
    def adb_idrometri_report_sync(
        source: OracleConnection, adb: AdbConnection
    ) -> SyncResult:
        """Copia l'intera IDROMETRI_REPORT dal database sorgente ad ADB (WKSP_DBPOA)."""

        inseriti = adb_sync_repo.sync_idrometri_report(source, adb)
        return SyncResult(inseriti=inseriti)

    return application


app = create_app()
