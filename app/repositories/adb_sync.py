"""Sincronizzazione verso il database Oracle ADB (schema WKSP_DBPOA).

Porting del modulo `adb` legacy (mai attivato in produzione: le route erano
commentate in `main.py`). Due differenze rispetto all'originale:

- lettura dalla sorgente a blocchi (`fetchmany` via `iter_chunks`) invece di
  `cursor.fetchall()` seguito da un unico `executemany`: evita di
  materializzare l'intera tabella in memoria, lo stesso rischio segnalato
  in `docs/CLAUDE.md` per IDROMETRI_REPORT, qui concreto perche' e' proprio
  una delle tabelle coinvolte;
- SELECT con colonne esplicite invece di `SELECT *`: il legacy si affidava
  all'ordine fisico delle colonne della tabella sorgente per farle
  combaciare con l'insert posizionale a destinazione (fragile e silenzioso
  in caso di mismatch). Le colonne qui sono le stesse gia' dichiarate dal
  legacy lato insert.

Scope temporaneo per MISURE_CAE (vedi `docs/refactor-decisions.md`,
sezione 7): si legge da MISURE_CAE_OLD sul database sorgente ARPAS/SASSARI,
non da MISURE_CAE (dati troppo recenti) ne' dalle tabelle annuali o dal
database separato con schema CAE, finche' non sono chiariti sovrapposizioni
e buchi di copertura tra le varie tabelle.
"""

import oracledb

from app.db import ARRAY_SIZE, iter_chunks, new_cursor

_SQL_SELECT_MISURE_CAE = """
    SELECT cod_staz, cod_grand, data_mis, valore, cod_valid, periodo_arc, ora, minuto
    FROM misure_cae_old
    ORDER BY cod_staz
"""

_SQL_INSERT_MISURE_CAE = """
    INSERT INTO wksp_dbpoa.misure_cae
        (cod_staz, cod_grand, data_mis, valore, cod_valid, periodo_arc, ora, minuto)
    VALUES (:1, :2, :3, :4, :5, :6, :7, :8)
"""

_SQL_SELECT_IDROMETRI_REPORT = """
    SELECT dataoper, nome, cod_staz, cod_grand, data_mis, s_min, s_max, var_s,
           valore, valore_prec, flag_inserito, descrizione
    FROM idrometri_report
    ORDER BY cod_staz, data_mis
"""

_SQL_INSERT_IDROMETRI_REPORT = """
    INSERT INTO wksp_dbpoa.idrometri_report
        (dataoper, nome, cod_staz, cod_grand, data_mis, s_min, s_max, var_s,
         valore, valore_prec, flag_inserito, descrizione)
    VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9, :10, :11, :12)
"""

_SQL_SAMPLE_MISURE_CAE_ADB = """
    SELECT * FROM wksp_dbpoa.misure_cae
    WHERE ROWNUM <= :quante
    ORDER BY cod_staz
"""


def fetch_misure_cae_adb_sample(
    connection: oracledb.Connection, quante: int = 8
) -> list[tuple]:
    """Lettura di controllo di poche righe gia' presenti su ADB (non un
    elenco completo: solo una verifica manuale, come il legacy `/adb_prima`).
    """

    cursor = new_cursor(connection)
    cursor.execute(_SQL_SAMPLE_MISURE_CAE_ADB, quante=quante)
    return list(cursor)


def _sync_table(
    source_connection: oracledb.Connection,
    adb_connection: oracledb.Connection,
    select_sql: str,
    insert_sql: str,
) -> int:
    source_cursor = new_cursor(source_connection)
    source_cursor.execute(select_sql)
    target_cursor = adb_connection.cursor()

    inseriti = 0
    for chunk in iter_chunks(source_cursor, ARRAY_SIZE):
        target_cursor.executemany(insert_sql, chunk)
        inseriti += target_cursor.rowcount

    adb_connection.commit()
    return inseriti


def sync_misure_cae(
    source_connection: oracledb.Connection, adb_connection: oracledb.Connection
) -> int:
    """Copia MISURE_CAE_OLD (sorgente) in WKSP_DBPOA.MISURE_CAE su ADB."""

    return _sync_table(
        source_connection,
        adb_connection,
        _SQL_SELECT_MISURE_CAE,
        _SQL_INSERT_MISURE_CAE,
    )


def sync_idrometri_report(
    source_connection: oracledb.Connection, adb_connection: oracledb.Connection
) -> int:
    """Copia l'intera IDROMETRI_REPORT sorgente in WKSP_DBPOA.IDROMETRI_REPORT."""

    return _sync_table(
        source_connection,
        adb_connection,
        _SQL_SELECT_IDROMETRI_REPORT,
        _SQL_INSERT_IDROMETRI_REPORT,
    )
