"""Catalogue des titres suivis : panel témoin et ETF de référence."""

import csv
from pathlib import Path

from bourse_jev.domaine.modeles import Titre
from bourse_jev.domaine.ports import Depot

ROLES = {"panel", "reference"}


def charger_panel(chemin: Path) -> list[Titre]:
    """Lit le CSV `symbole,nom,place,devise,role` ; `role` vaut `panel` ou `reference`."""
    titres = []
    with chemin.open(newline="", encoding="utf-8") as fichier:
        for ligne in csv.DictReader(fichier):
            role = ligne["role"].strip()
            if role not in ROLES:
                raise ValueError(f"{chemin.name} : rôle inconnu {role!r} pour {ligne['symbole']}")
            titres.append(
                Titre(
                    id=None,
                    symbole=ligne["symbole"].strip(),
                    place=ligne["place"].strip(),
                    nom=ligne["nom"].strip(),
                    devise=ligne["devise"].strip(),
                    actif=True,
                    panel_temoin=role == "panel",
                    est_reference=role == "reference",
                )
            )
    return titres


def synchroniser_catalogue(depot: Depot, titres: list[Titre]) -> int:
    """Ajoute au dépôt les titres absents ; renvoie le nombre de titres ajoutés."""
    return depot.enregistrer_titres(titres)
