"""Ligne de commande : `python -m bourse_jev migrer | catalogue | collecter`."""

import argparse
import sys
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from bourse_jev.adaptateurs.calendrier_xnys import CalendrierXNYS
from bourse_jev.adaptateurs.horloge import HorlogeSysteme
from bourse_jev.adaptateurs.postgres import DepotPostgres, appliquer_migrations, connecter
from bourse_jev.adaptateurs.twelve_data import SourceTwelveData
from bourse_jev.application.catalogue import charger_panel, synchroniser_catalogue
from bourse_jev.application.collecte import collecter
from bourse_jev.config import charger_configuration
from bourse_jev.domaine.erreurs import ConfigurationIncomplete
from bourse_jev.domaine.modeles import Declencheur, RapportExecution, StatutExecution
from bourse_jev.domaine.temps import jour_de_marche_courant

RACINE = Path(__file__).resolve().parents[2]
DOSSIER_MIGRATIONS = RACINE / "migrations"
PANEL_TEMOIN = RACINE / "config" / "panel_temoin.csv"


def lire_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    analyseur = argparse.ArgumentParser(prog="bourse_jev")
    commandes = analyseur.add_subparsers(dest="commande", required=True)
    commandes.add_parser("migrer", help="applique les migrations SQL manquantes")
    commandes.add_parser("catalogue", help="synchronise le panel témoin avec la base")
    collecte = commandes.add_parser("collecter", help="collecte les cours (avec rattrapage)")
    collecte.add_argument(
        "--date",
        type=date.fromisoformat,
        default=None,
        help="jour de marché AAAA-MM-JJ (défaut : aujourd'hui à New York)",
    )
    collecte.add_argument(
        "--declencheur",
        choices=[Declencheur.CRON.value, Declencheur.MANUEL.value],
        default=Declencheur.MANUEL.value,
    )
    return analyseur.parse_args(argv)


def code_de_sortie(statuts: Sequence[StatutExecution]) -> int:
    """0 si rien n'a échoué (partielle comprise), 1 si au moins un jour est en échec."""
    return 1 if StatutExecution.ECHEC in statuts else 0


def _une_ligne(texte: str) -> str:
    # Un message d'API est du contenu non fiable : sans saut de ligne, il ne peut pas forger
    # une commande de workflow GitHub (`::…::`) ; `%` est échappé comme l'exige GitHub.
    return texte.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _afficher(rapport: RapportExecution) -> None:
    print(
        f"{rapport.date_marche.isoformat()} : {rapport.statut}, "
        f"{rapport.nb_cours_enregistres} cours enregistrés, "
        f"{rapport.credits_consommes} crédits"
    )
    for erreur in rapport.erreurs:
        print(f"  - {_une_ligne(erreur)}")
    if rapport.titres_en_retard:
        print(f"  en retard (quota) : {', '.join(rapport.titres_en_retard)}")
    if rapport.statut is StatutExecution.PARTIELLE:
        print(
            f"::warning::Collecte partielle du {rapport.date_marche.isoformat()} : "
            f"{len(rapport.erreurs)} erreur(s), {len(rapport.titres_en_retard)} titre(s) en retard"
        )


def main(argv: Sequence[str] | None = None) -> int:
    args = lire_arguments(argv)
    try:
        configuration = charger_configuration()
    except ConfigurationIncomplete as erreur:
        print(f"Configuration incomplète : {erreur}", file=sys.stderr)
        return 2

    with connecter(configuration.database_url) as conn:
        if args.commande == "migrer":
            versions = appliquer_migrations(conn, DOSSIER_MIGRATIONS)
            print(f"Migrations appliquées : {', '.join(versions) or 'aucune'}")
            return 0

        depot = DepotPostgres(conn)
        if args.commande == "catalogue":
            ajoutes = synchroniser_catalogue(depot, charger_panel(PANEL_TEMOIN))
            print(f"Titres ajoutés au catalogue : {ajoutes}")
            return 0

        horloge = HorlogeSysteme()
        aujourd_hui = args.date or jour_de_marche_courant(horloge.maintenant())
        rapports = collecter(
            aujourd_hui,
            Declencheur(args.declencheur),
            depot,
            SourceTwelveData(configuration.twelve_data_api_key),
            CalendrierXNYS(),
            horloge,
        )
        if not rapports:
            print(f"{aujourd_hui.isoformat()} : rien à faire, tout est déjà collecté")
        for rapport in rapports:
            _afficher(rapport)
        return code_de_sortie([r.statut for r in rapports])


if __name__ == "__main__":
    sys.exit(main())
