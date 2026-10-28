from pathlib import Path

from bourse_jev.adaptateurs.memoire_depot import DepotEnMemoire
from bourse_jev.application.catalogue import charger_panel, synchroniser_catalogue

PANEL = Path(__file__).parents[2] / "config" / "panel_temoin.csv"


def test_panel_de_30_titres_et_une_reference():
    titres = charger_panel(PANEL)
    assert sum(t.panel_temoin for t in titres) == 30
    assert [t.symbole for t in titres if t.est_reference] == ["SPY"]


def test_synchronisation_idempotente():
    depot, titres = DepotEnMemoire(), charger_panel(PANEL)
    assert synchroniser_catalogue(depot, titres) == 31
    assert synchroniser_catalogue(depot, titres) == 0
