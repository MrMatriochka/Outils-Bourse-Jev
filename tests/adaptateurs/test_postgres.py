import psycopg
import pytest

from bourse_jev.adaptateurs.postgres import appliquer_migrations, connecter


def test_migrations_idempotentes(conn_test, dossier_migrations):
    assert appliquer_migrations(conn_test, dossier_migrations) == ["001_socle"]
    assert appliquer_migrations(conn_test, dossier_migrations) == []


def test_modification_d_un_cours_refusee_par_la_base(depot_postgres_avec_un_cours, conn_test):
    with pytest.raises(psycopg.errors.RaiseException, match="ajout seul"):
        conn_test.execute("UPDATE cours_journalier SET cloture = 1")


def test_connecter_reessaie_une_fois_apres_5_secondes():
    appels, attentes = [], []

    def ouvrir(dsn):
        appels.append(dsn)
        if len(appels) == 1:
            raise OSError("base en veille")
        return "connexion"

    assert connecter("dsn", attendre=attentes.append, ouvrir=ouvrir) == "connexion"
    assert attentes == [5.0]


def test_connecter_echoue_apres_deux_tentatives():
    def ouvrir(dsn):
        raise OSError("injoignable")

    with pytest.raises(OSError):
        connecter("dsn", attendre=lambda s: None, ouvrir=ouvrir)
