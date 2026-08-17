from app.models import Trascodifica
from app.repositories import trascodifiche as trascodifiche_repo
from tests.oracle_fakes import FakeConnection


def test_fetch_trascodifiche_cae_maps_rows_to_model() -> None:
    connection = FakeConnection([("Stazione Uno", "CAE01", "ARPA01")])

    result = trascodifiche_repo.fetch_trascodifiche_cae(connection)

    assert result == [
        Trascodifica(
            stazione="Stazione Uno", cod_staz_cae="CAE01", cod_staz_arpa="ARPA01"
        )
    ]
