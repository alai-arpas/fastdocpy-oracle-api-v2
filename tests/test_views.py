from app.models import Trascodifica
from app.views import render_trascodifica_page


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
