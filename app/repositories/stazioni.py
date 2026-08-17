"""Stazioni di rilevamento SASI e SAR (tabella STAZIONI)."""

import oracledb

from app.db import new_cursor
from app.models import Stazione

_TIPO_STAZ_SASI = "MTX"
_TIPO_STAZ_SAR = "SAR"

_SQL_STAZIONI_PER_TIPO = """
    SELECT cod_staz, nome
    FROM stazioni
    WHERE tipo_staz = :tipo_staz
    ORDER BY cod_staz
"""


def _fetch_stazioni(connection: oracledb.Connection, tipo_staz: str) -> list[Stazione]:
    cursor = new_cursor(connection)
    cursor.execute(_SQL_STAZIONI_PER_TIPO, tipo_staz=tipo_staz)
    return [Stazione(cod_staz=cod_staz, nome=nome) for cod_staz, nome in cursor]


def fetch_stazioni_sasi(connection: oracledb.Connection) -> list[Stazione]:
    return _fetch_stazioni(connection, _TIPO_STAZ_SASI)


def fetch_stazioni_sar(connection: oracledb.Connection) -> list[Stazione]:
    return _fetch_stazioni(connection, _TIPO_STAZ_SAR)
