from app.db import iter_chunks
from tests.oracle_fakes import FakeCursor


def test_iter_chunks_splits_rows_without_materializing_all_at_once() -> None:
    rows = [(i,) for i in range(7)]
    cursor = FakeCursor(rows)

    chunks = list(iter_chunks(cursor, size=3))

    assert chunks == [
        [(0,), (1,), (2,)],
        [(3,), (4,), (5,)],
        [(6,)],
    ]


def test_iter_chunks_on_empty_cursor_yields_nothing() -> None:
    cursor = FakeCursor([])

    assert list(iter_chunks(cursor, size=3)) == []
