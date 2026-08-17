from app.html import page_shell, render_table


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
