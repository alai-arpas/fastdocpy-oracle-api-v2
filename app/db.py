"""Connessione Oracle (thin mode) e helper condiviso per i cursori."""

from collections.abc import Iterator
from contextlib import contextmanager

import oracledb

from app.settings import OracleSettings

ARRAY_SIZE = 300


@contextmanager
def oracle_connection(oracle: OracleSettings) -> Iterator[oracledb.Connection]:
    """Apre una connessione Oracle per la durata del blocco `with`."""

    if oracle.credentials is None:
        raise RuntimeError(
            "Credenziali Oracle non configurate "
            "(FDP_ORACLE__CREDENTIALS__USER/PASSWORD)"
        )

    connection = oracledb.connect(
        user=oracle.credentials.user.get_secret_value(),
        password=oracle.credentials.password.get_secret_value(),
        dsn=oracle.dsn,
    )
    try:
        yield connection
    finally:
        connection.close()


def new_cursor(connection: oracledb.Connection) -> oracledb.Cursor:
    """Cursore con l'`arraysize` condiviso da tutte le repository."""

    cursor = connection.cursor()
    cursor.arraysize = ARRAY_SIZE
    return cursor
