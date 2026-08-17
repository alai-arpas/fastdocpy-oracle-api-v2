from app.repositories import adb_sync as adb_sync_repo
from tests.oracle_fakes import FakeConnection


def test_fetch_misure_cae_adb_sample_binds_quante() -> None:
    connection = FakeConnection([("101", "P1H", 12.3, "1")])

    result = adb_sync_repo.fetch_misure_cae_adb_sample(connection, quante=5)

    assert result == [("101", "P1H", 12.3, "1")]
    assert connection.fake_cursor.last_binds == {"quante": 5}


def test_sync_misure_cae_copies_all_rows_and_commits() -> None:
    rows = [(f"cod{i}", "P1H", "2022-11-15", 1.0, "1", "A", 3, 0) for i in range(5)]
    source = FakeConnection(rows)
    adb = FakeConnection([])

    inseriti = adb_sync_repo.sync_misure_cae(source, adb)

    assert inseriti == 5
    assert adb.fake_cursor.executemany_rows == rows
    assert adb.committed is True
    assert "misure_cae_old" in source.fake_cursor.last_sql.lower()
    assert "wksp_dbpoa.misure_cae" in adb.fake_cursor.executemany_sql.lower()


def test_sync_idrometri_report_copies_all_rows_and_commits() -> None:
    rows = [("op", "nome", "cod1", "LIT", "2022-11-15", 0, 1, 0, 0.5, 0.4, "S", "ok")]
    source = FakeConnection(rows)
    adb = FakeConnection([])

    inseriti = adb_sync_repo.sync_idrometri_report(source, adb)

    assert inseriti == 1
    assert adb.fake_cursor.executemany_rows == rows
    assert adb.committed is True
