"""Pagina di benvenuto in HTML (Pico.css).

L'elenco degli endpoint viene generato leggendo `application.routes`, non
scritto a mano: resta corretto da solo quando si aggiungono o si tolgono
route, senza bisogno di ricordarsi di aggiornare questa pagina.
"""

from html import escape

from fastapi import FastAPI
from fastapi.routing import APIRoute

_PICO_CSS_URL = "https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css"

# Ordine di visualizzazione delle sezioni; i tag non elencati qui finiscono
# in coda, in ordine alfabetico.
_TAG_ORDER = ["system", "stazioni", "trascodifiche", "misure", "adb"]
_TAG_LABELS = {
    "system": "Sistema",
    "stazioni": "Stazioni",
    "trascodifiche": "Trascodifiche",
    "misure": "Misure",
    "adb": "Sincronizzazione ADB",
}


def _short_description(route: APIRoute) -> str:
    if route.summary:
        return route.summary
    description = (route.description or "").strip()
    return description.splitlines()[0] if description else ""


def _route_link(route: APIRoute, method: str) -> str:
    path = escape(route.path)
    if method == "GET" and "{" not in route.path:
        return f'<a href="{path}"><code>{path}</code></a>'
    return f"<code>{path}</code>"


def _route_rows(routes: list[APIRoute]) -> str:
    rows = []
    for route in sorted(routes, key=lambda r: r.path):
        description = escape(_short_description(route))
        for method in sorted(route.methods - {"HEAD", "OPTIONS"}):
            rows.append(
                f"<tr><td>{method}</td><td>{_route_link(route, method)}</td>"
                f"<td>{description}</td></tr>"
            )
    return "\n".join(rows)


def _group_by_tag(application: FastAPI) -> dict[str, list[APIRoute]]:
    by_tag: dict[str, list[APIRoute]] = {}
    for route in application.routes:
        if not isinstance(route, APIRoute) or route.path == "/":
            continue
        tag = route.tags[0] if route.tags else "altro"
        by_tag.setdefault(tag, []).append(route)
    return by_tag


def render_home(application: FastAPI) -> str:
    """Home page HTML, con i link alle route effettivamente registrate."""

    by_tag = _group_by_tag(application)
    ordered_tags = [tag for tag in _TAG_ORDER if tag in by_tag]
    ordered_tags += sorted(tag for tag in by_tag if tag not in _TAG_ORDER)

    sections = "".join(
        f"""
        <section>
          <h2>{escape(_TAG_LABELS.get(tag, tag.capitalize()))}</h2>
          <table>
            <thead><tr><th>Metodo</th><th>Percorso</th><th>Descrizione</th></tr></thead>
            <tbody>
              {_route_rows(by_tag[tag])}
            </tbody>
          </table>
        </section>
        """
        for tag in ordered_tags
    )

    title = escape(application.title)
    description = escape(application.description or "")

    return f"""<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <link rel="stylesheet" href="{_PICO_CSS_URL}">
</head>
<body>
  <main class="container">
    <header>
      <h1>{title}</h1>
      <p>{description}</p>
      <p><a href="/docs" role="button">Documentazione interattiva (Swagger UI)</a></p>
    </header>
    {sections}
  </main>
</body>
</html>
"""
