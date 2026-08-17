from datetime import datetime

from app.models import MisuraCae
from app.repositories import misure_cae as misure_cae_repo
from tests.oracle_fakes import FakeConnection


def test_fetch_misure_cae_binds_params_and_maps_rows() -> None:
    riga = ("101", "P1H", 12.3, "1", datetime(2022, 11, 15, 3, 0))
    connection = FakeConnection([riga])
    inizio = datetime(2022, 11, 1)
    fine = datetime(2022, 11, 30)

    result = misure_cae_repo.fetch_misure_cae(
        connection, cod_grand="P1H", inizio=inizio, fine=fine
    )

    assert result == [
        MisuraCae(
            cod_staz="101",
            cod_grand="P1H",
            valore=12.3,
            cod_valid="1",
            data=datetime(2022, 11, 15, 3, 0),
        )
    ]
    assert connection.fake_cursor.last_binds == {
        "cod_grand": "P1H",
        "inizio": inizio,
        "fine": fine,
    }
    assert "misure_cae_old" in connection.fake_cursor.last_sql.lower()
