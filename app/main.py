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
from pydantic import BaseModel

from app.db import oracle_connection
from app.models import MisuraCae, Stazione, Trascodifica
from app.repositories import misure_cae as misure_cae_repo
from app.repositories import stazioni as stazioni_repo
from app.repositories import trascodifiche as trascodifiche_repo
from app.settings import AppSettings, get_settings


class HealthResponse(BaseModel):
    status: str
    service: str


def get_connection(request: Request) -> Iterator[oracledb.Connection]:
    """Connessione Oracle per la durata della richiesta."""

    settings: AppSettings = request.app.state.settings
    with oracle_connection(settings.oracle) as connection:
        yield connection


OracleConnection = Annotated[oracledb.Connection, Depends(get_connection)]


def create_app(settings: AppSettings | None = None) -> FastAPI:
    """Compone l'app senza aprire connessioni Oracle all'import."""

    runtime_settings = settings or get_settings()

    application = FastAPI(
        title="fastdocpy Oracle API v2",
        description="Refactoring del servizio dati idro-meteo ARPAS su Oracle.",
        version="0.1.0",
    )
    application.state.settings = runtime_settings

    @application.get("/", tags=["system"])
    def read_root() -> str:
        return "fastdocpy-oracle-api-v2"

    @application.get("/health", response_model=HealthResponse, tags=["system"])
    def health() -> HealthResponse:
        """Liveness del processo, senza verificare la raggiungibilita' di Oracle."""

        return HealthResponse(status="ok", service="fastdocpy-oracle-api-v2")

    @application.get("/sasi", response_model=list[Stazione], tags=["stazioni"])
    def sasi(connection: OracleConnection) -> list[Stazione]:
        return stazioni_repo.fetch_stazioni_sasi(connection)

    @application.get("/sar", response_model=list[Stazione], tags=["stazioni"])
    def sar(connection: OracleConnection) -> list[Stazione]:
        return stazioni_repo.fetch_stazioni_sar(connection)

    @application.get(
        "/trascodifica", response_model=list[Trascodifica], tags=["trascodifiche"]
    )
    def trascodifica(connection: OracleConnection) -> list[Trascodifica]:
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

    return application


app = create_app()
