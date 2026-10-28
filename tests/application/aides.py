"""Aides des tests de collecte : préparer et lire l'état du dépôt en mémoire."""

from datetime import UTC, date, datetime
from decimal import Decimal

from bourse_jev.adaptateurs.memoire_depot import DepotEnMemoire
from bourse_jev.domaine.modeles import (
    CoursJournalier,
    Declencheur,
    RapportExecution,
    StatutExecution,
)
from tests.doublures import fabriquer_cours

INSTANT = datetime(2026, 10, 28, 21, 45, tzinfo=UTC)


def marquer_reussi(depot: DepotEnMemoire, jour: date) -> None:
    eid = depot.debuter_execution(jour, Declencheur.CRON, INSTANT)
    depot.terminer_execution(eid, RapportExecution(jour, StatutExecution.OK, 0, [], [], 0), INSTANT)


def declencheur_enregistre(depot: DepotEnMemoire, jour: date) -> Declencheur:
    return depot.execution_du(jour)[0]


def id_de(depot: DepotEnMemoire, symbole: str) -> int:
    [titre] = [t for t in depot.titres_a_collecter() if t.symbole == symbole]
    assert titre.id is not None
    return titre.id


def cours_stocke(titre_id: int, jour: date, cloture: str) -> CoursJournalier:
    prix = Decimal(cloture)
    return fabriquer_cours(
        titre_id=titre_id, jour=jour, ouverture=prix, haut=prix, bas=prix, cloture=prix
    )


def cours_de(depot: DepotEnMemoire, symbole: str, jour: date) -> CoursJournalier | None:
    return depot.cours_du(id_de(depot, symbole), jour)
