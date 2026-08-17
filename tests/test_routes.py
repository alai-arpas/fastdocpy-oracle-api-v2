from contextlib import contextmanager
from datetime import date, datetime

from fastapi.testclient import TestClient

import app.main as main_module
from app.catalogo_misure import CatalogoMisure, VoceCatalogo
from app.main import create_app, get_adb_connection, get_connection
from tests.oracle_fakes import FakeConnection

_CATALOGO_DI_TEST = CatalogoMisure(
    voci=[
        VoceCatalogo(
            cod_staz="CA011B539",
            cod_grand="PCT",
            righe=1993201,
            data_min=date(2022, 1, 1),
            data_max=date(2025, 11, 15),
        )
    ]
)


def _client_with_fake_connection(rows: list[tuple]) -> TestClient:
    app = create_app()
    fake_connection = FakeConnection(rows)
    app.dependency_overrides[get_connection] = lambda: fake_connection
    return TestClient(app)


def _client_with_fake_connections(
    source_rows: list[tuple], adb_rows: list[tuple]
) -> tuple[TestClient, FakeConnection, FakeConnection]:
    app = create_app()
    source_connection = FakeConnection(source_rows)
    adb_connection = FakeConnection(adb_rows)
    app.dependency_overrides[get_connection] = lambda: source_connection
    app.dependency_overrides[get_adb_connection] = lambda: adb_connection
    return TestClient(app), source_connection, adb_connection


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


def test_trascodifica_html_route_returns_html_page() -> None:
    client = _client_with_fake_connection([("Stazione Uno", "CAE01", "ARPA01")])

    response = client.get("/html/trascodifica")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Stazione Uno" in response.text
    assert "CAE01" in response.text


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


def test_misure_cae_html_route_without_params_does_not_open_connection(
    monkeypatch,
) -> None:
    def _fail(**kwargs):
        raise AssertionError("oracle_connection non doveva essere chiamato")

    monkeypatch.setattr(main_module, "oracle_connection", _fail)
    client = TestClient(create_app())

    response = client.get("/html/misure_cae")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert 'action="/html/misure_cae"' in response.text


def test_misure_cae_html_route_with_params_queries_and_renders_table(
    monkeypatch,
) -> None:
    riga = ("101", "PCT", 1.5, "1", "2024-01-01T03:00:00")
    fake_connection = FakeConnection([riga])

    @contextmanager
    def _fake_oracle_connection(**kwargs):
        yield fake_connection

    monkeypatch.setattr(main_module, "oracle_connection", _fake_oracle_connection)
    client = TestClient(create_app())

    response = client.get(
        "/html/misure_cae",
        params={
            "cod_grand": "PCT",
            "inizio": "2024-01-01T00:00:00",
            "fine": "2024-01-02T00:00:00",
        },
    )

    assert response.status_code == 200
    assert "Risultati (1)" in response.text
    assert "101" in response.text
    assert fake_connection.fake_cursor.last_binds == {
        "cod_grand": "PCT",
        "inizio": datetime(2024, 1, 1),
        "fine": datetime(2024, 1, 2),
    }


def test_misure_cae_catalogo_route_returns_stazioni_e_grandezze() -> None:
    app = create_app()
    app.state.catalogo = _CATALOGO_DI_TEST
    client = TestClient(app)

    response = client.get("/misure_cae/catalogo")

    assert response.status_code == 200
    assert response.json() == {
        "stazioni": [
            {"codice": "CA011B539", "etichetta": "CA011B539 (1.993.201 righe)"}
        ],
        "grandezze": [{"codice": "PCT", "etichetta": "PCT (1.993.201 righe)"}],
    }


def test_misure_cae_catalogo_route_non_intercettata_da_cod_grand() -> None:
    """/misure_cae/catalogo deve restare distinta da /misure_cae/{cod_grand}:
    verifica che il routing non tratti "catalogo" come un valore di
    cod_grand (che darebbe 422, mancando inizio/fine)."""

    app = create_app()
    app.state.catalogo = _CATALOGO_DI_TEST
    client = TestClient(app)

    response = client.get("/misure_cae/catalogo")

    assert response.status_code == 200
    assert "stazioni" in response.json()


def test_misure_cae_catalogo_html_route_lists_stazioni_e_grandezze() -> None:
    app = create_app()
    app.state.catalogo = _CATALOGO_DI_TEST
    client = TestClient(app)

    response = client.get("/html/misure_cae/catalogo")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<td>CA011B539</td>" in response.text
    assert "<td>PCT</td>" in response.text


def test_adb_misure_cae_sample_route_returns_rows_from_adb() -> None:
    client, _source, _adb = _client_with_fake_connections(
        source_rows=[], adb_rows=[("101", "P1H", 12.3, "1")]
    )

    response = client.get("/adb/misure_cae")

    assert response.status_code == 200
    assert response.json() == [["101", "P1H", 12.3, "1"]]


def test_adb_misure_cae_sync_route_copies_source_rows_to_adb() -> None:
    rows = [("101", "P1H", "2022-11-15", 1.0, "1", "A", 3, 0)]
    client, _source, adb = _client_with_fake_connections(source_rows=rows, adb_rows=[])

    response = client.post("/adb/misure_cae/sync")

    assert response.status_code == 200
    assert response.json() == {"inseriti": 1}
    assert adb.committed is True


def test_adb_idrometri_report_sync_route_copies_source_rows_to_adb() -> None:
    rows = [("op", "nome", "cod1", "LIT", "2022-11-15", 0, 1, 0, 0.5, 0.4, "S", "ok")]
    client, _source, adb = _client_with_fake_connections(source_rows=rows, adb_rows=[])

    response = client.post("/adb/idrometri_report/sync")

    assert response.status_code == 200
    assert response.json() == {"inseriti": 1}
    assert adb.committed is True
