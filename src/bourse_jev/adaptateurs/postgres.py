"""Connexion Postgres, migrations et dépôt Postgres."""

import time
from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from bourse_jev.domaine.modeles import (
    CoursJournalier,
    Declencheur,
    RapportExecution,
    Titre,
)

Connexion = psycopg.Connection[Any]


def _ouvrir(dsn: str) -> Connexion:
    # Autocommit : chaque écriture du dépôt est validée aussitôt ; les migrations ouvrent
    # leur propre transaction.
    return psycopg.connect(dsn, autocommit=True)


def connecter(
    dsn: str,
    tentatives: int = 2,
    delai_s: float = 5.0,
    attendre: Callable[[float], None] = time.sleep,
    ouvrir: Callable[[str], Connexion] = _ouvrir,
) -> Connexion:
    """Ouvre la connexion ; réessaie après `delai_s` si la base (Neon) est en veille."""
    for tentative in range(1, tentatives + 1):
        try:
            return ouvrir(dsn)
        except (psycopg.OperationalError, OSError):
            if tentative == tentatives:
                raise
            attendre(delai_s)
    raise ValueError("tentatives doit valoir au moins 1")


def appliquer_migrations(conn: Connexion, dossier: Path) -> list[str]:
    """Applique, dans l'ordre, les migrations absentes ; renvoie les versions appliquées."""
    conn.execute(
        "create table if not exists schema_migrations ("
        " version text primary key,"
        " appliquee_le timestamptz not null default now())"
    )
    deja = {ligne[0] for ligne in conn.execute("select version from schema_migrations")}
    appliquees = []
    for chemin in sorted(dossier.glob("*.sql")):
        version = chemin.stem
        if version in deja:
            continue
        with conn.transaction():
            conn.execute(chemin.read_bytes())
            conn.execute("insert into schema_migrations (version) values (%s)", (version,))
        appliquees.append(version)
    return appliquees


class DepotPostgres:
    def __init__(self, conn: Connexion) -> None:
        self._conn = conn

    def enregistrer_titres(self, titres: list[Titre]) -> int:
        ajoutes = 0
        for t in titres:
            curseur = self._conn.execute(
                "insert into titre (symbole, place, nom, devise, actif, panel_temoin,"
                " est_reference) values (%s, %s, %s, %s, %s, %s, %s)"
                " on conflict (symbole, place) do nothing",
                (t.symbole, t.place, t.nom, t.devise, t.actif, t.panel_temoin, t.est_reference),
            )
            ajoutes += curseur.rowcount
        return ajoutes

    def titres_a_collecter(self) -> list[Titre]:
        lignes = self._conn.execute(
            "select id, symbole, place, nom, devise, actif, panel_temoin, est_reference"
            " from titre where actif order by id"
        )
        return [Titre(*ligne) for ligne in lignes]

    def cloture_precedente(self, titre_id: int, avant: date) -> Decimal | None:
        ligne = self._conn.execute(
            "select cloture from cours_journalier where titre_id = %s and jour < %s"
            " order by jour desc limit 1",
            (titre_id, avant),
        ).fetchone()
        return None if ligne is None else Decimal(ligne[0])

    def enregistrer_cours(self, cours: CoursJournalier) -> bool:
        curseur = self._conn.execute(
            "insert into cours_journalier (titre_id, jour, ouverture, haut, bas, cloture,"
            " volume, source, recupere_le) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
            " on conflict (titre_id, jour) do nothing",
            (
                cours.titre_id,
                cours.jour,
                cours.ouverture,
                cours.haut,
                cours.bas,
                cours.cloture,
                cours.volume,
                cours.source,
                cours.recupere_le,
            ),
        )
        return curseur.rowcount == 1

    def dates_reussies(self, depuis: date) -> set[date]:
        lignes = self._conn.execute(
            "select date_marche from execution"
            " where date_marche >= %s and statut in ('ok', 'sans_objet')",
            (depuis,),
        )
        return {ligne[0] for ligne in lignes}

    def debuter_execution(
        self, date_marche: date, declencheur: Declencheur, debut: datetime
    ) -> int:
        ligne = self._conn.execute(
            "insert into execution (date_marche, declencheur, statut, debut)"
            " values (%s, %s, 'en_cours', %s)"
            " on conflict (date_marche) do update set statut = 'en_cours',"
            " declencheur = excluded.declencheur, debut = excluded.debut, fin = null"
            " returning id",
            (date_marche, str(declencheur), debut),
        ).fetchone()
        assert ligne is not None
        return int(ligne[0])

    def terminer_execution(
        self, execution_id: int, rapport: RapportExecution, fin: datetime
    ) -> None:
        self._conn.execute(
            "update execution set statut = %s, fin = %s, nb_cours_enregistres = %s,"
            " erreurs = %s, titres_en_retard = %s, credits_consommes = %s where id = %s",
            (
                str(rapport.statut),
                fin,
                rapport.nb_cours_enregistres,
                Jsonb(rapport.erreurs),
                Jsonb(rapport.titres_en_retard),
                rapport.credits_consommes,
                execution_id,
            ),
        )
