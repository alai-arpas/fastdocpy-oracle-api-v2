from datetime import datetime

from app.models import MisuraCae, Trascodifica
from app.views import (
    _safe_json_for_script,
    render_misure_cae_page,
    render_trascodifica_page,
)


def test_render_trascodifica_page_lists_rows_and_links_home() -> None:
    rows = [
        Trascodifica(
            stazione="Stazione Uno", cod_staz_cae="CAE01", cod_staz_arpa="ARPA01"
        )
    ]

    html = render_trascodifica_page(rows)

    assert "Stazione Uno" in html
    assert "CAE01" in html
    assert "ARPA01" in html
    assert '<a href="/">' in html


def test_render_misure_cae_page_without_query_shows_docs_and_form_only() -> None:
    html = render_misure_cae_page(None, cod_grand=None, inizio=None, fine=None)

    assert "MISURE_CAE_OLD" in html
    assert '<form method="get" action="/html/misure_cae">' in html
    assert "Risultati" not in html


def test_render_misure_cae_page_with_empty_results_shows_message() -> None:
    html = render_misure_cae_page(
        [],
        cod_grand="PCT",
        inizio=datetime(2024, 1, 1),
        fine=datetime(2024, 1, 2),
    )

    assert "Nessun risultato" in html
    assert 'value="PCT"' in html
    assert 'value="2024-01-01T00:00"' in html


def test_render_misure_cae_page_preserves_cod_staz_in_form() -> None:
    html = render_misure_cae_page(
        None,
        cod_grand="PCT",
        inizio=None,
        fine=None,
        cod_staz="CA011B539",
    )

    assert 'name="cod_staz"' in html
    assert 'value="CA011B539"' in html


def test_render_misure_cae_page_with_rows_renders_table() -> None:
    rows = [
        MisuraCae(
            cod_staz="101",
            cod_grand="PCT",
            valore=1.5,
            cod_valid="1",
            data=datetime(2024, 1, 1, 3, 0),
        )
    ]

    html = render_misure_cae_page(
        rows,
        cod_grand="PCT",
        inizio=datetime(2024, 1, 1),
        fine=datetime(2024, 1, 2),
    )

    assert "Risultati (1)" in html
    assert "<td>101</td>" in html
    assert "<td>1.5</td>" in html


def test_render_misure_cae_page_escapes_cod_grand() -> None:
    html = render_misure_cae_page(None, cod_grand='"><script>', inizio=None, fine=None)

    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_render_misure_cae_page_with_cod_staz_shows_chart() -> None:
    rows = [
        MisuraCae(
            cod_staz="101",
            cod_grand="PCT",
            valore=1.5,
            cod_valid="1",
            data=datetime(2024, 1, 1, 3, 0),
        )
    ]

    html = render_misure_cae_page(
        rows,
        cod_grand="PCT",
        inizio=datetime(2024, 1, 1),
        fine=datetime(2024, 1, 2),
        cod_staz="101",
    )

    assert '<canvas id="misure-cae-chart">' in html
    assert "chart.umd.min.js" in html
    assert "Seleziona anche una stazione" not in html


def test_render_misure_cae_page_without_cod_staz_shows_hint_not_chart() -> None:
    rows = [
        MisuraCae(
            cod_staz="101",
            cod_grand="PCT",
            valore=1.5,
            cod_valid="1",
            data=datetime(2024, 1, 1, 3, 0),
        )
    ]

    html = render_misure_cae_page(
        rows,
        cod_grand="PCT",
        inizio=datetime(2024, 1, 1),
        fine=datetime(2024, 1, 2),
    )

    assert "Seleziona anche una stazione" in html
    assert '<canvas id="misure-cae-chart">' not in html


def test_safe_json_for_script_escapes_script_breakout() -> None:
    result = _safe_json_for_script("</script><script>alert(1)</script>")

    assert "</script>" not in result
    assert "\\u003c/script\\u003e" in result
