"""Boundary FastAPI del servizio Oracle idro-meteo (scheletro v2).

Le route legacy (misure, stazioni, validazioni CAE...) vanno migrate qui
progressivamente da fastdocpy-oracle-api; questo file parte volutamente
minimale, con solo root e health, per validare Docker/config prima del
porting della logica.
"""

from fastapi import FastAPI
from pydantic import BaseModel

from app.settings import AppSettings, get_settings


class HealthResponse(BaseModel):
    status: str
    service: str


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

    return application


app = create_app()
