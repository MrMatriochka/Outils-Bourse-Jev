"""Ports : ce dont le domaine et l'application ont besoin du monde extérieur."""

from datetime import date, datetime
from decimal import Decimal
from typing import Protocol

from bourse_jev.domaine.modeles import (
    CoursBrut,
    CoursJournalier,
    Declencheur,
    RapportExecution,
    Titre,
)


class Horloge(Protocol):
    def maintenant(self) -> datetime:
        """Instant présent, en UTC et avec fuseau."""
        ...


class CalendrierDeMarche(Protocol):
    def jours_de_bourse(self, debut: date, fin: date) -> list[date]:
        """Jours de séance entre `debut` et `fin` inclus, en ordre croissant."""
        ...


class SourceDeCours(Protocol):
    nom: str
    credits_consommes: int

    def cours_du_jour(self, symbole: str, jour: date) -> CoursBrut | None:
        """Cours de `symbole` pour `jour`, ou `None` s'il n'existe pas.

        Lève `QuotaAtteint` ou `SourceIndisponible`.
        """
        ...


class Depot(Protocol):
    def enregistrer_titres(self, titres: list[Titre]) -> int:
        """Ajoute les titres absents ; renvoie le nombre de titres ajoutés."""
        ...

    def titres_a_collecter(self) -> list[Titre]: ...

    def cloture_precedente(self, titre_id: int, avant: date) -> Decimal | None:
        """Dernière clôture connue strictement avant `avant`."""
        ...

    def enregistrer_cours(self, cours: CoursJournalier) -> bool:
        """Vrai si la ligne a été insérée, faux si elle existait déjà (jamais écrasée)."""
        ...

    def dates_reussies(self, depuis: date) -> set[date]:
        """Dates de marché à partir de `depuis` dont l'exécution est `ok` ou `sans_objet`."""
        ...

    def debuter_execution(
        self, date_marche: date, declencheur: Declencheur, debut: datetime
    ) -> int: ...

    def terminer_execution(
        self, execution_id: int, rapport: RapportExecution, fin: datetime
    ) -> None: ...
