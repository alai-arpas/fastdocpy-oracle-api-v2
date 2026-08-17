"""Doppi di test per connessione/cursore Oracle, senza dipendere da un DB reale."""

from typing import Any


class FakeCursor:
    def __init__(self, rows: list[tuple[Any, ...]] | None = None) -> None:
        self._rows = list(rows or [])
        self._position = 0
        self.arraysize: int | None = None
        self.last_sql: str | None = None
        self.last_binds: dict[str, Any] = {}
        self.executemany_sql: str | None = None
        self.executemany_rows: list[tuple[Any, ...]] = []
        self.rowcount = 0

    def execute(self, sql: str, **binds: Any) -> None:
        self.last_sql = sql
        self.last_binds = binds

    def executemany(self, sql: str, rows: list[tuple[Any, ...]]) -> None:
        self.executemany_sql = sql
        self.executemany_rows.extend(rows)
        self.rowcount = len(rows)

    def fetchmany(self, size: int) -> list[tuple[Any, ...]]:
        chunk = self._rows[self._position : self._position + size]
        self._position += len(chunk)
        return chunk

    def __iter__(self):
        return iter(self._rows)


class FakeConnection:
    """Espone lo stesso cursore ad ogni chiamata, cosi' i test possono
    ispezionare l'SQL/i bind usati e le righe inserite.
    """

    def __init__(self, rows: list[tuple[Any, ...]] | None = None) -> None:
        self.fake_cursor = FakeCursor(rows)
        self.committed = False

    def cursor(self) -> FakeCursor:
        return self.fake_cursor

    def commit(self) -> None:
        self.committed = True
