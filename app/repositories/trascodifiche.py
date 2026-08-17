"""Trascodifica stazioni CAE <-> ARPAS (tabella TRANSCODIFICHE_CAE_ARPAS)."""

import oracledb

from app.db import new_cursor
from app.models import Trascodifica

_SQL_TRASCODIFICHE_CAE = """
    SELECT stazione, cod_staz_cae, cod_staz_arpa
    FROM transcodifiche_cae_arpas
    ORDER BY cod_staz_arpa
"""


def fetch_trascodifiche_cae(connection: oracledb.Connection) -> list[Trascodifica]:
    cursor = new_cursor(connection)
    cursor.execute(_SQL_TRASCODIFICHE_CAE)
    return [
        Trascodifica(
            stazione=stazione, cod_staz_cae=cod_staz_cae, cod_staz_arpa=cod_staz_arpa
        )
        for stazione, cod_staz_cae, cod_staz_arpa in cursor
    ]
