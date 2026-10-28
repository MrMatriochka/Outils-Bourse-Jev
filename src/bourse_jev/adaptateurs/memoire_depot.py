"""Dépôt en mémoire : même contrat que le dépôt Postgres, pour les tests sans base."""

from dataclasses import dataclass, replace
from datetime import date, datetime
from decimal import Decimal

from bourse_jev.domaine.modeles import (
    CoursJournalier,
    Declencheur,
    RapportExecution,
    StatutExecution,
    Titre,
)

STATUTS_REUSSIS = {StatutExecution.OK, StatutExecution.SANS_OBJET}


@dataclass
class _Execution:
    id: int
    date_marche: date
    declencheur: Declencheur
    statut: StatutExecution
    debut: datetime
    fin: datetime | None = None
    rapport: RapportExecution | None = None


class DepotEnMemoire:
    def __init__(self) -> None:
        self._titres: dict[tuple[str, str], Titre] = {}
        self._cours: dict[tuple[int, date], CoursJournalier] = {}
        self._executions: dict[date, _Execution] = {}

    def enregistrer_titres(self, titres: list[Titre]) -> int:
        ajoutes = 0
        for titre in titres:
            cle = (titre.symbole, titre.place)
            if cle not in self._titres:
                self._titres[cle] = replace(titre, id=len(self._titres) + 1)
                ajoutes += 1
        return ajoutes

    def titres_a_collecter(self) -> list[Titre]:
        return [t for t in self._titres.values() if t.actif]

    def cloture_precedente(self, titre_id: int, avant: date) -> Decimal | None:
        anterieurs = [
            c for (tid, jour), c in self._cours.items() if tid == titre_id and jour < avant
        ]
        if not anterieurs:
            return None
        return max(anterieurs, key=lambda c: c.jour).cloture

    def enregistrer_cours(self, cours: CoursJournalier) -> bool:
        cle = (cours.titre_id, cours.jour)
        if cle in self._cours:
            return False
        self._cours[cle] = cours
        return True

    def dates_reussies(self, depuis: date) -> set[date]:
        return {
            e.date_marche
            for e in self._executions.values()
            if e.date_marche >= depuis and e.statut in STATUTS_REUSSIS
        }

    def debuter_execution(
        self, date_marche: date, declencheur: Declencheur, debut: datetime
    ) -> int:
        # Une relance du même jour réutilise la ligne, comme l'`ON CONFLICT` de Postgres.
        existante = self._executions.get(date_marche)
        identifiant = existante.id if existante else len(self._executions) + 1
        self._executions[date_marche] = _Execution(
            identifiant, date_marche, declencheur, StatutExecution.EN_COURS, debut
        )
        return identifiant

    def terminer_execution(
        self, execution_id: int, rapport: RapportExecution, fin: datetime
    ) -> None:
        execution = next(e for e in self._executions.values() if e.id == execution_id)
        execution.statut = rapport.statut
        execution.fin = fin
        execution.rapport = rapport
