from datetime import date

from bourse_jev.application.collecte import collecter
from bourse_jev.domaine.erreurs import QuotaAtteint, SourceIndisponible
from bourse_jev.domaine.modeles import Declencheur
from bourse_jev.domaine.modeles import StatutExecution as S
from tests.application.aides import (
    cours_de,
    cours_stocke,
    declencheur_enregistre,
    id_de,
    marquer_reussi,
)
from tests.doublures import CalendrierFactice, SourceFactice

L26, M27, ME28 = date(2026, 10, 26), date(2026, 10, 27), date(2026, 10, 28)
SAMEDI = date(2026, 10, 31)

# fixtures (conftest) : depot_3_titres (AAPL, MSFT, SPY), calendrier ([L26, M27, ME28]),
# horloge (28/10/2026 21:45 UTC), brut(jour, cloture="100") -> CoursBrut


def test_collecte_nominale(depot_3_titres, calendrier, horloge, source_complete):
    rapports = collecter(
        ME28,
        Declencheur.CRON,
        depot_3_titres,
        source_complete(ME28),
        calendrier,
        horloge,
        fenetre_rattrapage=1,
    )
    assert [(r.date_marche, r.statut, r.nb_cours_enregistres) for r in rapports] == [
        (ME28, S.OK, 3)
    ]


def test_deuxieme_execution_ne_fait_rien(depot_3_titres, calendrier, horloge, source_complete):
    src = source_complete(ME28)
    collecter(
        ME28, Declencheur.CRON, depot_3_titres, src, calendrier, horloge, fenetre_rattrapage=1
    )
    assert (
        collecter(
            ME28,
            Declencheur.MANUEL,
            depot_3_titres,
            src,
            calendrier,
            horloge,
            fenetre_rattrapage=1,
        )
        == []
    )


def test_jour_manque_rattrape_dans_l_ordre(depot_3_titres, calendrier, horloge, source_complete):
    marquer_reussi(depot_3_titres, L26)
    rapports = collecter(
        ME28, Declencheur.CRON, depot_3_titres, source_complete(M27, ME28), calendrier, horloge
    )
    assert [r.date_marche for r in rapports] == [M27, ME28]
    assert [declencheur_enregistre(depot_3_titres, d) for d in (M27, ME28)] == [
        Declencheur.RATTRAPAGE,
        Declencheur.CRON,
    ]


def test_rattrapage_limite_a_la_fenetre(depot_3_titres, calendrier, horloge, source_complete):
    rapports = collecter(
        ME28,
        Declencheur.CRON,
        depot_3_titres,
        source_complete(M27, ME28),
        calendrier,
        horloge,
        fenetre_rattrapage=2,
    )
    assert [r.date_marche for r in rapports] == [M27, ME28]


def test_jour_non_ouvre_marque_sans_objet(depot_3_titres, horloge):
    rapports = collecter(
        SAMEDI, Declencheur.CRON, depot_3_titres, SourceFactice({}), CalendrierFactice([]), horloge
    )
    assert [(r.date_marche, r.statut) for r in rapports] == [(SAMEDI, S.SANS_OBJET)]


def test_erreur_sur_un_titre_n_arrete_pas_les_autres(depot_3_titres, calendrier, horloge, brut):
    src = SourceFactice(
        {
            ("AAPL", ME28): brut(ME28),
            ("MSFT", ME28): SourceIndisponible("MSFT : 404"),
            ("SPY", ME28): brut(ME28),
        }
    )
    [r] = collecter(
        ME28, Declencheur.CRON, depot_3_titres, src, calendrier, horloge, fenetre_rattrapage=1
    )
    assert r.statut is S.PARTIELLE and r.nb_cours_enregistres == 2
    assert any("MSFT" in e for e in r.erreurs)


def test_cours_absent_n_est_pas_remplace_par_la_veille(depot_3_titres, calendrier, horloge, brut):
    src = SourceFactice({("AAPL", M27): brut(M27)})
    [r] = collecter(
        ME28, Declencheur.CRON, depot_3_titres, src, calendrier, horloge, fenetre_rattrapage=1
    )
    assert r.statut is S.ECHEC and r.nb_cours_enregistres == 0
    assert any("cours absent" in e for e in r.erreurs)


def test_cours_aberrant_rejete(depot_3_titres, calendrier, horloge, brut):
    tid = id_de(depot_3_titres, "AAPL")
    depot_3_titres.enregistrer_cours(cours_stocke(tid, M27, cloture="100"))
    src = SourceFactice(
        {
            ("AAPL", ME28): brut(ME28, cloture="200"),
            ("MSFT", ME28): brut(ME28),
            ("SPY", ME28): brut(ME28),
        }
    )
    [r] = collecter(
        ME28, Declencheur.CRON, depot_3_titres, src, calendrier, horloge, fenetre_rattrapage=1
    )
    assert any("AAPL" in e and "variation_aberrante" in e for e in r.erreurs)


def test_quota_atteint_reporte_les_titres_restants(depot_3_titres, calendrier, horloge, brut):
    src = SourceFactice({("AAPL", ME28): brut(ME28), ("MSFT", ME28): QuotaAtteint("800/jour")})
    [r] = collecter(
        ME28, Declencheur.CRON, depot_3_titres, src, calendrier, horloge, fenetre_rattrapage=1
    )
    assert r.statut is S.PARTIELLE and r.titres_en_retard == ["MSFT", "SPY"]


def test_recupere_le_vient_de_l_horloge(depot_3_titres, calendrier, horloge, source_complete):
    collecter(
        ME28,
        Declencheur.CRON,
        depot_3_titres,
        source_complete(ME28),
        calendrier,
        horloge,
        fenetre_rattrapage=1,
    )
    assert cours_de(depot_3_titres, "AAPL", ME28).recupere_le == horloge.maintenant()
