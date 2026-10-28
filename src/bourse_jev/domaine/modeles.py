"""Modèles du domaine : valeurs immuables, montants en `Decimal`."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum


@dataclass(frozen=True)
class Titre:
    id: int | None
    symbole: str
    place: str
    nom: str
    devise: str
    actif: bool
    panel_temoin: bool
    est_reference: bool


@dataclass(frozen=True)
class CoursBrut:
    """Cours d'une séance tel que le renvoie une source, avant rattachement à un titre."""

    jour: date
    ouverture: Decimal
    haut: Decimal
    bas: Decimal
    cloture: Decimal
    volume: int


@dataclass(frozen=True)
class CoursJournalier:
    """Cours stocké : rattaché à un titre, avec sa source et son horodatage de connaissance."""

    titre_id: int
    jour: date
    ouverture: Decimal
    haut: Decimal
    bas: Decimal
    cloture: Decimal
    volume: int
    source: str
    recupere_le: datetime


class StatutExecution(StrEnum):
    EN_COURS = "en_cours"
    OK = "ok"
    PARTIELLE = "partielle"
    SANS_OBJET = "sans_objet"
    ECHEC = "echec"


class Declencheur(StrEnum):
    CRON = "cron"
    MANUEL = "manuel"
    RATTRAPAGE = "rattrapage"


@dataclass(frozen=True)
class RapportExecution:
    date_marche: date
    statut: StatutExecution
    nb_cours_enregistres: int
    erreurs: list[str]
    titres_en_retard: list[str]
    credits_consommes: int
