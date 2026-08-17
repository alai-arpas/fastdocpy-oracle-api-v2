"""Doppi di test per connessione/cursore Oracle, senza dipendere da un DB reale."""

from typing import Any


class FakeCursor:
    def __init__(self, rows: list[tuple[Any, ...]]) -> None:
        self._rows = rows
        self.arraysize: int | None = None
        self.last_sql: str | None = None
        self.last_binds: dict[str, Any] = {}

    def execute(self, sql: str, **binds: Any) -> None:
        self.last_sql = sql
        self.last_binds = binds

    def __iter__(self):
        return iter(self._rows)


class FakeConnection:
    """Espone lo stesso cursore ad ogni chiamata, cosi' i test possono
    ispezionare l'SQL e i bind usati dall'ultima query eseguita.
    """

    def __init__(self, rows: list[tuple[Any, ...]]) -> None:
        self.fake_cursor = FakeCursor(rows)

    def cursor(self) -> FakeCursor:
        return self.fake_cursor
