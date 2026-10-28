import os
from pathlib import Path

import psycopg
import pytest

from bourse_jev.domaine.modeles import Titre
from tests.doublures import fabriquer_cours

RACINE = Path(__file__).parents[1]


@pytest.fixture
def dossier_migrations():
    return RACINE / "migrations"


@pytest.fixture
def conn_test():
    """Connexion à la base de test, sur un schéma vidé ; test sauté sans `TEST_DATABASE_URL`."""
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL absent : base Postgres de test indisponible")
    conn = psycopg.connect(url, autocommit=True)
    conn.execute("DROP SCHEMA public CASCADE")
    conn.execute("CREATE SCHEMA public")
    yield conn
    conn.close()


@pytest.fixture
def depot_postgres(conn_test, dossier_migrations):
    from bourse_jev.adaptateurs.postgres import DepotPostgres, appliquer_migrations

    appliquer_migrations(conn_test, dossier_migrations)
    return DepotPostgres(conn_test)


@pytest.fixture
def depot_postgres_avec_un_cours(depot_postgres):
    depot_postgres.enregistrer_titres(
        [Titre(None, "AAPL", "XNYS", "Apple", "USD", True, True, False)]
    )
    tid = depot_postgres.titres_a_collecter()[0].id
    depot_postgres.enregistrer_cours(fabriquer_cours(titre_id=tid))
    return depot_postgres
