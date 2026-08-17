from app.html import page_shell, render_filterable_table, render_table


def test_page_shell_includes_title_description_and_pico_css() -> None:
    html = page_shell("Titolo", "Descrizione", "<p>corpo</p>")

    assert "<title>Titolo</title>" in html
    assert "Descrizione" in html
    assert "pico" in html.lower()
    assert "<p>corpo</p>" in html


def test_page_shell_home_link_is_optional() -> None:
    without_link = page_shell("T", "D", "body")
    with_link = page_shell("T", "D", "body", show_home_link=True)

    assert '<a href="/">' not in without_link
    assert '<a href="/">' in with_link


def test_render_table_escapes_cell_content() -> None:
    html = render_table(["A", "B"], [("<script>", "safe")])

    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "<td>safe</td>" in html


def test_render_table_sets_id_when_given() -> None:
    without_id = render_table(["A"], [("1",)])
    with_id = render_table(["A"], [("1",)], table_id="una-tabella")

    assert "<table>" in without_id
    assert '<table id="una-tabella">' in with_id


def test_render_filterable_table_includes_search_input_and_table() -> None:
    html = render_filterable_table(
        "tabella-prova", ["Codice"], [("PCT",), ("TCI",)], placeholder="Cerca…"
    )

    assert '<table id="tabella-prova">' in html
    assert 'id="filtro-tabella-prova"' in html
    assert 'placeholder="Cerca…"' in html
    assert "<td>PCT</td>" in html
    assert "<td>TCI</td>" in html
    assert 'document.getElementById("tabella-prova")' in html
