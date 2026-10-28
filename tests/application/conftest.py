from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from bourse_jev.adaptateurs.memoire_depot import DepotEnMemoire
from bourse_jev.domaine.modeles import CoursBrut, Titre
from tests.doublures import CalendrierFactice, HorlogeFixe, SourceFactice

SYMBOLES = ("AAPL", "MSFT", "SPY")


def fabriquer_brut(jour: date, cloture: str = "100") -> CoursBrut:
    prix = Decimal(cloture)
    return CoursBrut(jour, prix, prix, prix, prix, 1000)


@pytest.fixture
def depot_3_titres():
    depot = DepotEnMemoire()
    depot.enregistrer_titres(
        [Titre(None, s, "XNYS", s, "USD", True, s != "SPY", s == "SPY") for s in SYMBOLES]
    )
    return depot


@pytest.fixture
def calendrier():
    return CalendrierFactice([date(2026, 10, 26), date(2026, 10, 27), date(2026, 10, 28)])


@pytest.fixture
def horloge():
    return HorlogeFixe(datetime(2026, 10, 28, 21, 45, tzinfo=UTC))


@pytest.fixture
def brut():
    return fabriquer_brut


@pytest.fixture
def source_complete():
    def fabriquer(*jours: date) -> SourceFactice:
        return SourceFactice({(s, j): fabriquer_brut(j) for s in SYMBOLES for j in jours})

    return fabriquer
