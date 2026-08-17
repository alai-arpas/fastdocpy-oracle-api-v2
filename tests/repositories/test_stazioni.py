from app.models import Stazione
from app.repositories import stazioni as stazioni_repo
from tests.oracle_fakes import FakeConnection


def test_fetch_stazioni_sasi_binds_tipo_staz_mtx() -> None:
    connection = FakeConnection([("101", "Stazione Uno"), ("102", "Stazione Due")])

    result = stazioni_repo.fetch_stazioni_sasi(connection)

    assert result == [
        Stazione(cod_staz="101", nome="Stazione Uno"),
        Stazione(cod_staz="102", nome="Stazione Due"),
    ]
    assert connection.fake_cursor.last_binds == {"tipo_staz": "MTX"}


def test_fetch_stazioni_sar_binds_tipo_staz_sar() -> None:
    connection = FakeConnection([("201", "Stazione Sar")])

    result = stazioni_repo.fetch_stazioni_sar(connection)

    assert result == [Stazione(cod_staz="201", nome="Stazione Sar")]
    assert connection.fake_cursor.last_binds == {"tipo_staz": "SAR"}
