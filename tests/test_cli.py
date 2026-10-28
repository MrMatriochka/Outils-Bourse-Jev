from bourse_jev.__main__ import code_de_sortie, lire_arguments
from bourse_jev.domaine.modeles import StatutExecution as S


def test_arguments_collecter():
    args = lire_arguments(["collecter", "--date", "2026-10-28", "--declencheur", "manuel"])
    assert args.commande == "collecter" and str(args.date) == "2026-10-28"
    assert args.declencheur == "manuel"


def test_date_par_defaut_absente():
    assert lire_arguments(["collecter"]).date is None


def test_code_de_sortie():
    assert code_de_sortie([]) == 0
    assert code_de_sortie([S.OK, S.PARTIELLE, S.SANS_OBJET]) == 0
    assert code_de_sortie([S.OK, S.ECHEC]) == 1


def test_message_d_api_ne_peut_pas_forger_une_commande_de_workflow(capsys):
    from datetime import date

    from bourse_jev.__main__ import _afficher
    from bourse_jev.domaine.modeles import RapportExecution

    erreur = "AAPL : erreur 400 (x\n::error::injecté)"
    _afficher(RapportExecution(date(2026, 10, 28), S.PARTIELLE, 1, [erreur], [], 2))
    lignes = capsys.readouterr().out.splitlines()
    assert not any(ligne.startswith("::error::") for ligne in lignes)


def test_configuration_incomplete_renvoie_2(monkeypatch):
    from bourse_jev.__main__ import main

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("TWELVE_DATA_API_KEY", raising=False)
    assert main(["migrer"]) == 2


def test_migrer_puis_catalogue_sur_la_base_de_test(conn_test, monkeypatch):
    import os

    from bourse_jev.__main__ import main

    monkeypatch.setenv("DATABASE_URL", os.environ["TEST_DATABASE_URL"])
    monkeypatch.setenv("TWELVE_DATA_API_KEY", "factice")
    assert main(["migrer"]) == 0
    assert main(["catalogue"]) == 0
    assert conn_test.execute("select count(*) from titre").fetchone() == (31,)
