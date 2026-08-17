"""Connessione Oracle (thin mode) e helper condivisi per i cursori."""

from collections.abc import Iterator
from contextlib import contextmanager

import oracledb

from app.settings import OracleCredentials

ARRAY_SIZE = 300


@contextmanager
def oracle_connection(
    *, dsn: str, credentials: OracleCredentials | None
) -> Iterator[oracledb.Connection]:
    """Apre una connessione Oracle per la durata del blocco `with`.

    Generica rispetto al database di destinazione (sorgente ARPAS o ADB):
    entrambe si autenticano con utente/password su una DSN, cambia solo la
    provenienza di `dsn`/`credentials` nel chiamante.
    """

    if credentials is None:
        raise RuntimeError(f"Credenziali Oracle non configurate per {dsn!r}")

    connection = oracledb.connect(
        user=credentials.user.get_secret_value(),
        password=credentials.password.get_secret_value(),
        dsn=dsn,
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


def iter_chunks(
    cursor: oracledb.Cursor, size: int = ARRAY_SIZE
) -> Iterator[list[tuple]]:
    """Legge il cursore a blocchi di `size` righe.

    A differenza di `cursor.fetchall()`, non materializza mai l'intero
    result set in memoria: usato dalle sincronizzazioni verso ADB, dove le
    tabelle sorgente (es. IDROMETRI_REPORT) possono essere grandi.
    """

    while True:
        rows = cursor.fetchmany(size)
        if not rows:
            return
        yield rows
