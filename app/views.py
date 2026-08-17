"""Viste HTML (Pico.css) sopra i dati esposti dalle API JSON.

Ogni funzione qui prende i dati gia' letti da una repository e li rende in
tabella con `app.html.render_table`, dentro la stessa shell della home page.
"""

import json
from datetime import datetime
from html import escape

from app.catalogo_misure import CatalogoMisure, OpzioneSelezione
from app.html import page_shell, render_filterable_table, render_table
from app.models import MisuraCae, Trascodifica

_CHART_JS_URL = "https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"


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
      caratteri). 27 codici confermati nei dati reali (2022-2025):
      <code>PCT</code> (pioggia, di gran lunga il piu' numeroso — oltre
      258 milioni di righe su 132 stazioni), <code>TCI</code>
      (temperatura), <code>LIT</code>/<code>LJT</code> (livello primo/
      secondo idrometro), <code>DVM</code>/<code>DVA</code> (direzione
      vento), <code>VAM</code>/<code>VAV</code> (velocita' vento),
      <code>UCI</code>, <code>TCM</code>, <code>TCL</code>,
      <code>TCH</code>, <code>UCH</code>, <code>UCL</code>,
      <code>VAI</code>, <code>VAH</code>, <code>VAL</code>,
      <code>TCG</code>, <code>UCG</code>, <code>PCG</code>,
      <code>DVG</code>, <code>VAG</code>, <code>DVH</code>,
      <code>VAD</code>, <code>DVV</code>, <code>LIH</code>,
      <code>LIL</code> (questi ultimi con volumi/copertura stazioni molto
      minori — probabili varianti statistiche istantaneo/media/min/max,
      non ancora confermato). Le select qui sotto sono popolate dallo
      stesso catalogo esposto su
      <a href="/html/misure_cae/catalogo">/html/misure_cae/catalogo</a>
      (anche in JSON su <code>GET /misure_cae/catalogo</code>).</li>
    <li><code>inizio</code> / <code>fine</code>: intervallo di data/ora in
      formato ISO&nbsp;8601 (es. <code>2024-01-01T00:00</code>).</li>
    <li><code>cod_staz</code>: facoltativo. Se assente restituisce tutte le
      stazioni; se presente filtra su una sola (max 9 caratteri) e mostra
      anche un grafico valore/tempo (serve una singola stazione: con piu'
      stazioni insieme un grafico a linee non sarebbe leggibile).</li>
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


def _select_options(opzioni: list[OpzioneSelezione], selezionato: str | None) -> str:
    return "".join(
        f'<option value="{escape(opz.codice)}"'
        f"{' selected' if opz.codice == selezionato else ''}>"
        f"{escape(opz.etichetta)}</option>"
        for opz in opzioni
    )


def _misure_cae_form(
    cod_grand: str | None,
    inizio: datetime | None,
    fine: datetime | None,
    cod_staz: str | None,
    grandezze: list[OpzioneSelezione],
    stazioni: list[OpzioneSelezione],
) -> str:
    def fmt(value: datetime | None) -> str:
        return value.strftime("%Y-%m-%dT%H:%M") if value else ""

    grandezza_vuota = not any(opz.codice == cod_grand for opz in grandezze)
    grandezza_placeholder = (
        f'<option value="" disabled {"selected" if grandezza_vuota else ""}>'
        "seleziona una grandezza…</option>"
    )

    return f"""
    <form method="get" action="/html/misure_cae">
      <div class="grid">
        <label>Grandezza (cod_grand)
          <select name="cod_grand" required>
            {grandezza_placeholder}
            {_select_options(grandezze, cod_grand)}
          </select>
        </label>
        <label>Stazione (cod_staz, facoltativo)
          <select name="cod_staz">
            <option value="">tutte le stazioni</option>
            {_select_options(stazioni, cod_staz)}
          </select>
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
    <p><a href="/html/misure_cae/catalogo">Vedi il catalogo completo di
    stazioni e grandezze &rarr;</a></p>
    """


def _safe_json_for_script(value: object) -> str:
    """`json.dumps` non basta dentro un `<script>`: se il valore contiene
    `</script>` (es. un `cod_staz` malevolo passato come query param), il
    tokenizzatore HTML del browser chiuderebbe il tag lo stesso, a
    prescindere dal contesto JS. Si esclude escapando `<`, `>`, `&`.
    """

    return (
        json.dumps(value)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


def _misure_cae_chart(rows: list[MisuraCae], cod_staz: str, cod_grand: str) -> str:
    labels_json = _safe_json_for_script([row.data.isoformat() for row in rows])
    valori_json = _safe_json_for_script([row.valore for row in rows])
    label_json = _safe_json_for_script(f"{cod_grand} — {cod_staz}")

    return f"""
    <h2>Grafico</h2>
    <div style="height: 320px">
      <canvas id="misure-cae-chart"></canvas>
    </div>
    <script src="{_CHART_JS_URL}"></script>
    <script>
      (function () {{
        const dark = window.matchMedia("(prefers-color-scheme: dark)").matches;
        const line = dark ? "#3987e5" : "#2a78d6";
        const ink = dark ? "#c3c2b7" : "#52514e";
        const grid = dark ? "#2c2c2a" : "#e1e0d9";

        new Chart(document.getElementById("misure-cae-chart"), {{
          type: "line",
          data: {{
            labels: {labels_json},
            datasets: [{{
              label: {label_json},
              data: {valori_json},
              borderColor: line,
              backgroundColor: line,
              borderWidth: 2,
              pointRadius: 0,
              tension: 0.15,
            }}],
          }},
          options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{ legend: {{ display: false }} }},
            scales: {{
              x: {{
                ticks: {{ color: ink, maxRotation: 0, autoSkip: true }},
                grid: {{ color: grid }},
              }},
              y: {{ ticks: {{ color: ink }}, grid: {{ color: grid }} }},
            }},
          }},
        }});
      }})();
    </script>
    """


def render_misure_cae_page(
    rows: list[MisuraCae] | None,
    *,
    cod_grand: str | None,
    inizio: datetime | None,
    fine: datetime | None,
    cod_staz: str | None = None,
    grandezze: list[OpzioneSelezione] | None = None,
    stazioni: list[OpzioneSelezione] | None = None,
) -> str:
    """Documentazione + form di ricerca; interroga solo se cod_grand/inizio/
    fine sono presenti (`rows` e' `None` quando la pagina e' vista senza
    query). `cod_staz` resta facoltativo anche in ricerca. `grandezze`/
    `stazioni` popolano le select del form (dal catalogo caricato
    all'avvio); vuote se il catalogo non e' disponibile.
    """

    parts = [
        _MISURE_CAE_DOC,
        _misure_cae_form(
            cod_grand, inizio, fine, cod_staz, grandezze or [], stazioni or []
        ),
    ]

    if rows is not None:
        if rows and cod_staz and cod_grand:
            parts.append(_misure_cae_chart(rows, cod_staz, cod_grand))
        elif rows and not cod_staz:
            parts.append(
                "<p>Seleziona anche una stazione per vedere il grafico "
                "(con piu' stazioni insieme non sarebbe leggibile).</p>"
            )

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


def render_catalogo_page(catalogo: CatalogoMisure) -> str:
    """Catalogo di stazioni/grandezze note, caricato da un CSV di
    riferimento all'avvio del processo (`app.catalogo_misure`).
    """

    intro = f"""
    <section>
      <h2>Cosa contiene</h2>
      <p>Catalogo di stazioni e grandezze note in <code>MISURE_CAE_OLD</code>,
      caricato all'avvio da un export CSV di riferimento
      (<code>app/data/misure_cae_old.csv</code>) — non e' letto dal
      database in tempo reale, quindi puo' non riflettere dati aggiunti
      dopo l'estrazione. {len(catalogo.stazioni)} stazioni,
      {len(catalogo.grandezze)} grandezze. Dettagli in
      <code>docs/refactor-decisions.md</code>, sezione 8.</p>
    </section>
    """

    grandezze_table = render_filterable_table(
        "tabella-grandezze",
        ["Grandezza", "Righe totali"],
        [(opz.codice, opz.etichetta) for opz in catalogo.grandezze],
        placeholder="Filtra per grandezza…",
    )
    stazioni_table = render_filterable_table(
        "tabella-stazioni",
        ["Stazione", "Righe totali"],
        [(opz.codice, opz.etichetta) for opz in catalogo.stazioni],
        placeholder="Filtra per stazione…",
    )
    dettaglio_table = render_filterable_table(
        "tabella-dettaglio",
        ["Stazione", "Grandezza", "Righe", "Da", "A"],
        [
            (voce.cod_staz, voce.cod_grand, voce.righe, voce.data_min, voce.data_max)
            for voce in sorted(catalogo.voci, key=lambda v: (v.cod_staz, v.cod_grand))
        ],
        placeholder="Filtra per stazione o grandezza…",
    )

    body = f"""
    {intro}
    <section>
      <h2>Grandezze ({len(catalogo.grandezze)})</h2>
      {grandezze_table}
    </section>
    <section>
      <h2>Stazioni ({len(catalogo.stazioni)})</h2>
      {stazioni_table}
    </section>
    <section>
      <h2>Dettaglio completo (stazione &times; grandezza)</h2>
      {dettaglio_table}
    </section>
    """

    return page_shell(
        "Catalogo misure CAE",
        "Stazioni e grandezze note per MISURE_CAE_OLD, con volume e copertura.",
        body,
        show_home_link=True,
    )
