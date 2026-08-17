"""Viste HTML (Pico.css) sopra i dati esposti dalle API JSON.

Ogni funzione qui prende i dati gia' letti da una repository e li rende in
tabella con `app.html.render_table`, dentro la stessa shell della home page.
"""

from datetime import datetime
from html import escape

from app.html import page_shell, render_table
from app.models import MisuraCae, Trascodifica


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


_MISURE_CAE_DOC = """
<section>
  <h2>Cosa sono questi dati</h2>
  <p>Misure di validazione CAE (pioggia, temperatura, livelli idrometrici),
  stessa fonte dell'endpoint JSON <code>GET /misure_cae/{cod_grand}</code>.</p>

  <h3>Parametri</h3>
  <ul>
    <li><code>cod_grand</code>: codice della grandezza misurata (max 3
      caratteri). Esempi osservati nei dati reali: <code>PCT</code>,
      <code>VAM</code>, <code>VAV</code>, <code>DVA</code>,
      <code>DVM</code>. L'elenco completo dei codici non e' ancora
      documentato in modo affidabile.</li>
    <li><code>inizio</code> / <code>fine</code>: intervallo di data/ora in
      formato ISO&nbsp;8601 (es. <code>2024-01-01T00:00</code>).</li>
  </ul>

  <article>
    <strong>Scope attuale (provvisorio).</strong> Questa vista legge da
    <code>MISURE_CAE_OLD</code>, non da <code>MISURE_CAE</code>: la
    famiglia di tabelle MISURE_CAE e' divisa per periodo e restano punti
    da chiarire (sovrapposizioni tra tabelle, un buco di copertura di
    alcuni mesi, un secondo database con schema leggermente diverso).
    Dettagli in <code>docs/refactor-decisions.md</code>, sezione 7.
  </article>
</section>
"""


def _misure_cae_form(
    cod_grand: str | None, inizio: datetime | None, fine: datetime | None
) -> str:
    def fmt(value: datetime | None) -> str:
        return value.strftime("%Y-%m-%dT%H:%M") if value else ""

    return f"""
    <form method="get" action="/html/misure_cae">
      <div class="grid">
        <label>Grandezza (cod_grand)
          <input type="text" name="cod_grand" maxlength="3" required
                 placeholder="es. PCT" value="{escape(cod_grand or "")}">
        </label>
        <label>Inizio
          <input type="datetime-local" name="inizio" required
                 value="{escape(fmt(inizio))}">
        </label>
        <label>Fine
          <input type="datetime-local" name="fine" required
                 value="{escape(fmt(fine))}">
        </label>
      </div>
      <button type="submit">Cerca</button>
    </form>
    """


def render_misure_cae_page(
    rows: list[MisuraCae] | None,
    *,
    cod_grand: str | None,
    inizio: datetime | None,
    fine: datetime | None,
) -> str:
    """Documentazione + form di ricerca; interroga solo se i tre parametri
    sono presenti (`rows` e' `None` quando la pagina e' vista senza query).
    """

    parts = [_MISURE_CAE_DOC, _misure_cae_form(cod_grand, inizio, fine)]

    if rows is not None:
        if rows:
            headers = ["Stazione", "Grandezza", "Valore", "Validazione", "Data"]
            table_rows = [
                (row.cod_staz, row.cod_grand, row.valore, row.cod_valid, row.data)
                for row in rows
            ]
            parts.append(f"<h2>Risultati ({len(rows)})</h2>")
            parts.append(render_table(headers, table_rows))
        else:
            parts.append("<p>Nessun risultato per i parametri indicati.</p>")

    body = "\n".join(parts)

    return page_shell(
        "Misure CAE",
        "Ricerca e documentazione delle misure di validazione CAE.",
        body,
        show_home_link=True,
    )
