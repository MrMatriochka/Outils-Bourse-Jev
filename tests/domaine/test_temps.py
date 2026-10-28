from datetime import UTC, date, datetime

from bourse_jev.domaine.temps import jour_de_marche_courant


def test_jour_de_marche_courant_utilise_new_york():
    # 29/10/2026 à 3 h 30 UTC = 28/10/2026 à 23 h 30 à New York
    instant = datetime(2026, 10, 29, 3, 30, tzinfo=UTC)
    assert jour_de_marche_courant(instant) == date(2026, 10, 28)


def test_jour_de_marche_courant_apres_la_cloture():
    instant = datetime(2026, 10, 28, 21, 45, tzinfo=UTC)
    assert jour_de_marche_courant(instant) == date(2026, 10, 28)
