from datetime import date
from pathlib import Path

from app.catalogo_misure import (
    CatalogoMisure,
    VoceCatalogo,
    carica_catalogo,
    get_catalogo,
)


def test_carica_catalogo_con_file_mancante_restituisce_catalogo_vuoto(
    tmp_path: Path,
) -> None:
    catalogo = carica_catalogo(tmp_path / "non-esiste.csv")

    assert catalogo.voci == []
    assert catalogo.stazioni == []
    assert catalogo.grandezze == []


def test_carica_catalogo_legge_righe_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / "misure.csv"
    csv_path.write_text(
        '"COD_STAZ";"COD_GRAND";"RIGHE";"DATA_MIN";"DATA_MAX";\n'
        '"CA011B539";"PCT";"1993201";"01-GEN-22";"15-NOV-25";\n',
        encoding="utf-8",
    )

    catalogo = carica_catalogo(csv_path)

    assert catalogo.voci == [
        VoceCatalogo(
            cod_staz="CA011B539",
            cod_grand="PCT",
            righe=1993201,
            data_min=date(2022, 1, 1),
            data_max=date(2025, 11, 15),
        )
    ]


def test_catalogo_stazioni_aggrega_righe_per_stazione() -> None:
    catalogo = CatalogoMisure(
        voci=[
            VoceCatalogo(
                cod_staz="B",
                cod_grand="PCT",
                righe=10,
                data_min=date(2022, 1, 1),
                data_max=date(2022, 1, 2),
            ),
            VoceCatalogo(
                cod_staz="B",
                cod_grand="TCI",
                righe=5,
                data_min=date(2022, 1, 1),
                data_max=date(2022, 1, 2),
            ),
            VoceCatalogo(
                cod_staz="A",
                cod_grand="PCT",
                righe=1,
                data_min=date(2022, 1, 1),
                data_max=date(2022, 1, 2),
            ),
        ]
    )

    stazioni = catalogo.stazioni

    assert [opz.codice for opz in stazioni] == ["A", "B"]
    assert stazioni[1].etichetta == "B (15 righe)"


def test_catalogo_grandezze_ordina_per_volume_decrescente() -> None:
    catalogo = CatalogoMisure(
        voci=[
            VoceCatalogo(
                cod_staz="A",
                cod_grand="RARO",
                righe=1,
                data_min=date(2022, 1, 1),
                data_max=date(2022, 1, 2),
            ),
            VoceCatalogo(
                cod_staz="A",
                cod_grand="PCT",
                righe=1000,
                data_min=date(2022, 1, 1),
                data_max=date(2022, 1, 2),
            ),
        ]
    )

    grandezze = catalogo.grandezze

    assert [opz.codice for opz in grandezze] == ["PCT", "RARO"]


def test_get_catalogo_legge_il_csv_reale_del_progetto() -> None:
    catalogo = get_catalogo()

    codici_grandezze = {opz.codice for opz in catalogo.grandezze}
    assert "PCT" in codici_grandezze
    assert len(catalogo.stazioni) > 0
