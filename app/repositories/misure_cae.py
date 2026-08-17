"""Misure di validazione CAE (tabella MISURE_CAE_OLD, database sorgente ARPAS).

Il legacy costruiva le date con `to_date('...', 'dd-mm-yyyy hh24:mi')` a
partire da stringhe passate cosi' come sono nella request, interpolate nel
testo SQL. Qui `inizio`/`fine` arrivano come `datetime` gia' validati da
FastAPI e vengono legati come bind variable: `oracledb` li converte da solo
in colonne DATE/TIMESTAMP, senza bisogno di formattare date in SQL.

Scope temporaneo (vedi `docs/refactor-decisions.md`, sezione 7): la
famiglia MISURE_CAE e' divisa in piu' tabelle per anno/periodo, e c'e'
anche un database separato (schema CAE) con una struttura leggermente
diversa. Finche' questi punti non sono chiariti, si legge solo da
MISURE_CAE_OLD sul database ARPAS/SASSARI gia' configurato
(FDP_ORACLE__*) — non MISURE_CAE (dati troppo recenti, ~ultimi giorni) ne'
le altre tabelle annuali/il database CAE.
"""

from datetime import datetime

import oracledb

from app.db import new_cursor
from app.models import MisuraCae

_SQL_MISURE_CAE = """
    SELECT cod_staz, cod_grand, valore, cod_valid, TRUNC(data_mis, 'HH24') AS data
    FROM misure_cae_old
    WHERE cod_grand = :cod_grand
      AND data_mis >= :inizio
      AND data_mis <= :fine
      {filtro_stazione}
    ORDER BY cod_staz, TRUNC(data_mis, 'HH24'), cod_grand
"""


def fetch_misure_cae(
    connection: oracledb.Connection,
    *,
    cod_grand: str,
    inizio: datetime,
    fine: datetime,
    cod_staz: str | None = None,
) -> list[MisuraCae]:
    """`cod_staz` e' opzionale: se assente non filtra per stazione.

    Il legacy aveva questa idea abbozzata (`filtra_stazione` in
    `query_idro_valida.py`) ma commentata, e con interpolazione diretta
    del valore nel testo SQL invece di un bind variable. Qui la struttura
    della query varia (clausola presente o assente), ma il valore di
    `cod_staz` e' sempre legato come bind, mai interpolato.
    """

    binds: dict[str, object] = {"cod_grand": cod_grand, "inizio": inizio, "fine": fine}
    filtro_stazione = ""
    if cod_staz:
        filtro_stazione = "AND cod_staz = :cod_staz"
        binds["cod_staz"] = cod_staz

    sql = _SQL_MISURE_CAE.format(filtro_stazione=filtro_stazione)
    cursor = new_cursor(connection)
    cursor.execute(sql, **binds)
    return [
        MisuraCae(
            cod_staz=cod_staz_val,
            cod_grand=cod_grand_val,
            valore=valore,
            cod_valid=cod_valid,
            data=data,
        )
        for cod_staz_val, cod_grand_val, valore, cod_valid, data in cursor
    ]
