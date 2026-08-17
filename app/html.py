"""Shell HTML (Pico.css) condivisa dalle pagine del servizio.

Usata sia dalla home page (`app/home.py`) sia dalle viste HTML sopra i dati
delle API JSON (`app/views.py`), per non duplicare il boilerplate
`<head>`/Pico.css in ogni pagina.
"""

from collections.abc import Iterable, Sequence
from html import escape

PICO_CSS_URL = "https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css"


def page_shell(
    title: str, description: str, body: str, *, show_home_link: bool = False
) -> str:
    """Documento HTML completo attorno a `body`, con il foglio di stile Pico.css."""

    home_link = '<p><a href="/">&larr; Home</a></p>' if show_home_link else ""

    return f"""<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <link rel="stylesheet" href="{PICO_CSS_URL}">
</head>
<body>
  <main class="container">
    <header>
      <h1>{escape(title)}</h1>
      <p>{escape(description)}</p>
      {home_link}
    </header>
    {body}
  </main>
</body>
</html>
"""


def render_table(
    headers: Sequence[str],
    rows: Iterable[Sequence[object]],
    *,
    table_id: str | None = None,
) -> str:
    """Tabella HTML da intestazioni ed elenco di righe (celle convertite a testo).

    `table_id` e' un identificativo scelto dallo sviluppatore (non da input
    utente): serve ad agganciarci un filtro via `render_filterable_table`,
    non richiede quindi escaping per contenuto esterno.
    """

    id_attr = f' id="{table_id}"' if table_id else ""
    head_cells = "".join(f"<th>{escape(header)}</th>" for header in headers)
    body_rows = "\n".join(
        "<tr>" + "".join(f"<td>{escape(str(cell))}</td>" for cell in row) + "</tr>"
        for row in rows
    )

    return f"""
    <table{id_attr}>
      <thead><tr>{head_cells}</tr></thead>
      <tbody>
        {body_rows}
      </tbody>
    </table>
    """


def render_filterable_table(
    table_id: str,
    headers: Sequence[str],
    rows: Iterable[Sequence[object]],
    *,
    placeholder: str = "Filtra…",
) -> str:
    """Tabella con una casella di ricerca (tipo il filtro di Excel): nasconde
    dal vivo, lato client, le righe che non contengono il testo digitato in
    nessuna colonna (confronto case-insensitive). Adatta a tabelle fino a
    qualche migliaio di righe gia' presenti nella pagina — non e' una
    ricerca lato server, non aiuta con result set enormi non paginati.
    """

    filtro_id = f"filtro-{table_id}"
    table_html = render_table(headers, rows, table_id=table_id)

    return f"""
    <input type="search" id="{filtro_id}" placeholder="{escape(placeholder)}"
           aria-controls="{table_id}">
    {table_html}
    <script>
      (function () {{
        const input = document.getElementById("{filtro_id}");
        const corpo = document.getElementById("{table_id}").tBodies[0];
        input.addEventListener("input", function () {{
          const termine = input.value.trim().toLowerCase();
          for (const riga of corpo.rows) {{
            riga.style.display = riga.textContent.toLowerCase().includes(termine)
              ? ""
              : "none";
          }}
        }});
      }})();
    </script>
    """
