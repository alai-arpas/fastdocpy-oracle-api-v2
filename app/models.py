"""Modelli Pydantic delle risposte, in sostituzione dei dict costruiti a mano
(`dict(zip(campi, valori))`) del servizio legacy.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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
    """Misura da tabella MISURE_CAE, troncata all'ora come nel legacy.

    Vincoli di lunghezza allineati al DDL: COD_STAZ VARCHAR2(9), COD_GRAND
    VARCHAR2(3), COD_VALID VARCHAR2(1).
    """

    model_config = ConfigDict(frozen=True)

    cod_staz: str = Field(max_length=9)
    cod_grand: str = Field(max_length=3)
    valore: float | None
    cod_valid: str | None = Field(default=None, max_length=1)
    data: datetime
