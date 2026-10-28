"""Chargement de la configuration depuis les variables d'environnement."""

import os
from collections.abc import Mapping
from dataclasses import dataclass

from bourse_jev.domaine.erreurs import ConfigurationIncomplete

VARIABLES_OBLIGATOIRES = ("DATABASE_URL", "TWELVE_DATA_API_KEY")


@dataclass(frozen=True)
class Configuration:
    database_url: str
    twelve_data_api_key: str


def charger_configuration(env: Mapping[str, str] = os.environ) -> Configuration:
    """Lit la configuration ; lève `ConfigurationIncomplete` en nommant les variables manquantes.

    Le message ne contient que des noms de variables, jamais de valeur : il finit dans les
    journaux de GitHub Actions.
    """
    manquantes = [nom for nom in VARIABLES_OBLIGATOIRES if not env.get(nom, "").strip()]
    if manquantes:
        raise ConfigurationIncomplete(
            "Variables d'environnement manquantes ou vides : " + ", ".join(manquantes)
        )
    return Configuration(
        database_url=env["DATABASE_URL"].strip(),
        twelve_data_api_key=env["TWELVE_DATA_API_KEY"].strip(),
    )
