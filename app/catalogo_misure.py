"""Catalogo di stazioni e grandezze note per MISURE_CAE_OLD.

Caricato una volta all'avvio da `app/data/misure_cae_old.csv`, un export
generato dall'utente con una query di aggregazione (`COD_STAZ, COD_GRAND,
COUNT(*), MIN(DATA_MIS), MAX(DATA_MIS)`) sul database reale — vedi
`docs/refactor-decisions.md`, sezione 8.

Non e' la fonte di verita' (che resta il database): serve solo a popolare
le selezioni stazione/grandezza nell'interfaccia, cosi' l'utente sceglie da
un elenco invece di dover ricordare a memoria 163 codici stazione e 27
codici grandezza.
"""

import csv
from datetime import date
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict

_CSV_PATH = Path(__file__).resolve().parent / "data" / "misure_cae_old.csv"

_MESI_IT = {
    "GEN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAG": 5,
    "GIU": 6,
    "LUG": 7,
    "AGO": 8,
    "SET": 9,
    "OTT": 10,
    "NOV": 11,
    "DIC": 12,
}


class VoceCatalogo(BaseModel):
    """Una combinazione stazione/grandezza, con volume e copertura note."""

    model_config = ConfigDict(frozen=True)

    cod_staz: str
    cod_grand: str
    righe: int
    data_min: date
    data_max: date


class OpzioneSelezione(BaseModel):
    """Un'opzione per una `<select>`: codice piu' un'etichetta leggibile."""

    model_config = ConfigDict(frozen=True)

    codice: str
    etichetta: str


class CatalogoMisure(BaseModel):
    """Catalogo completo, con le viste derivate gia' pronte per le select."""

    model_config = ConfigDict(frozen=True)

    voci: list[VoceCatalogo]

    @property
    def stazioni(self) -> list[OpzioneSelezione]:
        """Stazioni distinte, ordinate per codice, con il totale righe."""

        totali: dict[str, int] = {}
        for voce in self.voci:
            totali[voce.cod_staz] = totali.get(voce.cod_staz, 0) + voce.righe
        return [
            OpzioneSelezione(codice=cod, etichetta=f"{cod} ({_fmt_int(righe)} righe)")
            for cod, righe in sorted(totali.items())
        ]

    @property
    def grandezze(self) -> list[OpzioneSelezione]:
        """Grandezze distinte, ordinate per volume (le piu' usate prima)."""

        totali: dict[str, int] = {}
        for voce in self.voci:
            totali[voce.cod_grand] = totali.get(voce.cod_grand, 0) + voce.righe
        return [
            OpzioneSelezione(codice=cod, etichetta=f"{cod} ({_fmt_int(righe)} righe)")
            for cod, righe in sorted(totali.items(), key=lambda kv: -kv[1])
        ]


class CatalogoResponse(BaseModel):
    """Risposta JSON di `GET /misure_cae/catalogo`."""

    model_config = ConfigDict(frozen=True)

    stazioni: list[OpzioneSelezione]
    grandezze: list[OpzioneSelezione]


def _fmt_int(valore: int) -> str:
    return f"{valore:,}".replace(",", ".")


def _parse_data_it(valore: str) -> date:
    giorno, mese, anno = valore.strip().strip('"').split("-")
    anno_int = int(anno)
    anno_int += 2000 if anno_int < 70 else 1900
    return date(anno_int, _MESI_IT[mese.upper()], int(giorno))


def carica_catalogo(percorso: Path = _CSV_PATH) -> CatalogoMisure:
    """Legge il CSV di riferimento.

    Se il file manca restituisce un catalogo vuoto invece di sollevare
    un'eccezione: e' un dato accessorio per l'interfaccia, non deve
    impedire l'avvio dell'app se non e' presente.
    """

    if not percorso.exists():
        return CatalogoMisure(voci=[])

    voci: list[VoceCatalogo] = []
    with percorso.open(encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=";")
        next(reader, None)  # intestazione
        for riga in reader:
            if not riga or not riga[0]:
                continue
            cod_staz, cod_grand, righe, data_min, data_max = (
                campo.strip('"') for campo in riga[:5]
            )
            voci.append(
                VoceCatalogo(
                    cod_staz=cod_staz,
                    cod_grand=cod_grand,
                    righe=int(righe),
                    data_min=_parse_data_it(data_min),
                    data_max=_parse_data_it(data_max),
                )
            )

    return CatalogoMisure(voci=voci)


@lru_cache
def get_catalogo() -> CatalogoMisure:
    """Carica il catalogo una sola volta per processo."""

    return carica_catalogo()
