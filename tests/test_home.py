from fastapi.testclient import TestClient

from app.home import render_home
from app.main import create_app


def test_root_route_returns_html_with_pico_css() -> None:
    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "pico" in response.text.lower()


def test_render_home_links_to_registered_get_routes_without_path_params() -> None:
    application = create_app()

    html = render_home(application)

    assert '<a href="/health">' in html
    assert '<a href="/sasi">' in html
    assert '<a href="/sar">' in html
    assert '<a href="/trascodifica">' in html
    assert '<a href="/html/trascodifica">' in html


def test_render_home_does_not_link_routes_with_path_params_or_non_get() -> None:
    application = create_app()

    html = render_home(application)

    assert "<code>/misure_cae/{cod_grand}</code>" in html
    assert '<a href="/misure_cae/{cod_grand}">' not in html
    assert "<code>/adb/misure_cae/sync</code>" in html
    assert '<a href="/adb/misure_cae/sync">' not in html


def test_render_home_excludes_root_route_itself() -> None:
    application = create_app()

    html = render_home(application)

    assert '<a href="/">' not in html
