from datetime import UTC, date, datetime
from decimal import Decimal as D

from bourse_jev.domaine.modeles import Declencheur, RapportExecution, StatutExecution, Titre
from tests.doublures import fabriquer_cours

DEBUT = datetime(2026, 10, 27, 21, 45, tzinfo=UTC)


def titre(symbole, actif=True, panel=True, reference=False):
    return Titre(None, symbole, "XNYS", symbole, "USD", actif, panel, reference)


def test_enregistrer_titres_est_idempotent(depot):
    assert depot.enregistrer_titres([titre("AAPL"), titre("MSFT")]) == 2
    assert depot.enregistrer_titres([titre("AAPL")]) == 0
    assert sorted(t.symbole for t in depot.titres_a_collecter()) == ["AAPL", "MSFT"]


def test_titres_inactifs_exclus_de_la_collecte(depot):
    depot.enregistrer_titres([titre("AAPL"), titre("OLD", actif=False)])
    assert [t.symbole for t in depot.titres_a_collecter()] == ["AAPL"]


def test_cours_jamais_ecrase(depot):
    depot.enregistrer_titres([titre("AAPL")])
    tid = depot.titres_a_collecter()[0].id
    assert depot.enregistrer_cours(fabriquer_cours(titre_id=tid)) is True
    assert depot.enregistrer_cours(fabriquer_cours(titre_id=tid, cloture=D("100.5"))) is False
    assert depot.cloture_precedente(tid, avant=date(2026, 10, 28)) == D("100")


def test_cloture_precedente_strictement_avant(depot):
    depot.enregistrer_titres([titre("AAPL")])
    tid = depot.titres_a_collecter()[0].id
    depot.enregistrer_cours(fabriquer_cours(titre_id=tid, jour=date(2026, 10, 26), cloture=D("99")))
    depot.enregistrer_cours(
        fabriquer_cours(titre_id=tid, jour=date(2026, 10, 27), cloture=D("100"))
    )
    assert depot.cloture_precedente(tid, avant=date(2026, 10, 27)) == D("99")
    assert depot.cloture_precedente(tid, avant=date(2026, 10, 26)) is None


def test_execution_relancee_reutilise_la_meme_ligne(depot):
    a = depot.debuter_execution(date(2026, 10, 27), Declencheur.CRON, DEBUT)
    b = depot.debuter_execution(date(2026, 10, 27), Declencheur.MANUEL, DEBUT)
    assert a == b


def test_dates_reussies_ne_contiennent_que_ok_et_sans_objet(depot):
    statuts = [
        (27, StatutExecution.OK),
        (26, StatutExecution.PARTIELLE),
        (25, StatutExecution.SANS_OBJET),
    ]
    for jour, statut in statuts:
        d = date(2026, 10, jour)
        eid = depot.debuter_execution(d, Declencheur.CRON, DEBUT)
        depot.terminer_execution(eid, RapportExecution(d, statut, 0, [], [], 0), DEBUT)
    assert depot.dates_reussies(depuis=date(2026, 10, 1)) == {
        date(2026, 10, 27),
        date(2026, 10, 25),
    }
