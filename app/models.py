"""Modelli Pydantic delle risposte, in sostituzione dei dict costruiti a mano
(`dict(zip(campi, valori))`) del servizio legacy.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class Stazione(BaseModel):
    """Riga della tabella STAZIONI (sottoinsieme usato dagli endpoint SASI/SAR)."""

    model_config = ConfigDict(frozen=True)

    cod_staz: str
    nome: str


class Trascodifica(BaseModel):
    """Riga di TRANSCODIFICHE_CAE_ARPAS: corrispondenza stazione CAE <-> ARPAS."""

    model_config = ConfigDict(frozen=True)

    stazione: str
    cod_staz_cae: str
    cod_staz_arpa: str


class MisuraCae(BaseModel):
    """Misura da tabella MISURE_CAE, troncata all'ora come nel legacy."""

    model_config = ConfigDict(frozen=True)

    cod_staz: str
    cod_grand: str
    valore: float | None
    cod_valid: str | None
    data: datetime
