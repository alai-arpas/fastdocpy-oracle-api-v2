"""Viste HTML (Pico.css) sopra i dati esposti dalle API JSON.

Ogni funzione qui prende i dati gia' letti da una repository e li rende in
tabella con `app.html.render_table`, dentro la stessa shell della home page.
"""

from app.html import page_shell, render_table
from app.models import Trascodifica


def render_trascodifica_page(rows: list[Trascodifica]) -> str:
    headers = ["Stazione", "Cod. stazione CAE", "Cod. stazione ARPAS"]
    table_rows = [(row.stazione, row.cod_staz_cae, row.cod_staz_arpa) for row in rows]

    body = render_table(headers, table_rows)

    return page_shell(
        "Trascodifiche CAE ↔ ARPAS",
        "Corrispondenza tra stazioni CAE e stazioni ARPAS.",
        body,
        show_home_link=True,
    )
