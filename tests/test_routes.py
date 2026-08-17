from fastapi.testclient import TestClient

from app.main import create_app, get_connection
from tests.oracle_fakes import FakeConnection


def _client_with_fake_connection(rows: list[tuple]) -> TestClient:
    app = create_app()
    fake_connection = FakeConnection(rows)
    app.dependency_overrides[get_connection] = lambda: fake_connection
    return TestClient(app)


def test_sasi_route_returns_stazioni_from_repository() -> None:
    client = _client_with_fake_connection([("101", "Stazione Uno")])

    response = client.get("/sasi")

    assert response.status_code == 200
    assert response.json() == [{"cod_staz": "101", "nome": "Stazione Uno"}]


def test_sar_route_returns_stazioni_from_repository() -> None:
    client = _client_with_fake_connection([("201", "Stazione Sar")])

    response = client.get("/sar")

    assert response.status_code == 200
    assert response.json() == [{"cod_staz": "201", "nome": "Stazione Sar"}]


def test_trascodifica_route_returns_trascodifiche_from_repository() -> None:
    client = _client_with_fake_connection([("Stazione Uno", "CAE01", "ARPA01")])

    response = client.get("/trascodifica")

    assert response.status_code == 200
    assert response.json() == [
        {"stazione": "Stazione Uno", "cod_staz_cae": "CAE01", "cod_staz_arpa": "ARPA01"}
    ]


def test_misure_cae_route_returns_misure_from_repository() -> None:
    riga = ("101", "P1H", 12.3, "1", "2022-11-15T03:00:00")
    client = _client_with_fake_connection([riga])

    response = client.get(
        "/misure_cae/P1H",
        params={"inizio": "2022-11-01T00:00:00", "fine": "2022-11-30T00:00:00"},
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "cod_staz": "101",
            "cod_grand": "P1H",
            "valore": 12.3,
            "cod_valid": "1",
            "data": "2022-11-15T03:00:00",
        }
    ]
