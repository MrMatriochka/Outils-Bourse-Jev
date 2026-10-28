from datetime import date

from bourse_jev.adaptateurs.calendrier_xnys import CalendrierXNYS


def test_semaine_de_thanksgiving_2026():
    jours = CalendrierXNYS().jours_de_bourse(date(2026, 11, 23), date(2026, 11, 29))
    # 26/11 Thanksgiving fermé ; 27/11 clôture anticipée mais ouvert ; week-end exclu
    assert jours == [date(2026, 11, 23), date(2026, 11, 24), date(2026, 11, 25), date(2026, 11, 27)]


def test_fete_nationale_observee_le_vendredi_3_juillet_2026():
    jours = CalendrierXNYS().jours_de_bourse(date(2026, 6, 29), date(2026, 7, 3))
    assert date(2026, 7, 3) not in jours


def test_intervalle_sans_jour_de_bourse():
    assert CalendrierXNYS().jours_de_bourse(date(2026, 10, 31), date(2026, 11, 1)) == []
