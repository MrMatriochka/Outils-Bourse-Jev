"""Doublures partagées par les tests."""

from dataclasses import fields
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from bourse_jev.domaine.modeles import CoursBrut, CoursJournalier


class HorlogeFixe:
    def __init__(self, instant: datetime) -> None:
        self.instant = instant

    def maintenant(self) -> datetime:
        return self.instant


def fabriquer_cours(**modifs: Any) -> CoursJournalier:
    """Cours normal du titre 1 au 27/10/2026 ; chaque argument nommé remplace un champ."""
    valeurs: dict[str, Any] = {
        "titre_id": 1,
        "jour": date(2026, 10, 27),
        "ouverture": Decimal("100"),
        "haut": Decimal("101"),
        "bas": Decimal("99"),
        "cloture": Decimal("100"),
        "volume": 1000,
        "source": "test",
        "recupere_le": datetime(2026, 10, 27, 21, 45, tzinfo=UTC),
    }
    inconnus = set(modifs) - {f.name for f in fields(CoursJournalier)}
    if inconnus:
        raise TypeError(f"champs inconnus : {sorted(inconnus)}")
    valeurs.update(modifs)
    return CoursJournalier(**valeurs)


class SourceFactice:
    """Source scriptée : `(symbole, jour)` → cours ou exception levée ; absent → `None`."""

    nom = "factice"

    def __init__(self, reponses: dict[tuple[str, date], CoursBrut | Exception]) -> None:
        self.reponses = reponses
        self.credits_consommes = 0

    def cours_du_jour(self, symbole: str, jour: date) -> CoursBrut | None:
        self.credits_consommes += 1
        reponse = self.reponses.get((symbole, jour))
        if isinstance(reponse, Exception):
            raise reponse
        return reponse


class CalendrierFactice:
    def __init__(self, jours: list[date]) -> None:
        self.jours = sorted(jours)

    def jours_de_bourse(self, debut: date, fin: date) -> list[date]:
        return [j for j in self.jours if debut <= j <= fin]
