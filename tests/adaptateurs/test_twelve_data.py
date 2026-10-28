import json
import os
from datetime import date, timedelta
from decimal import Decimal as D
from pathlib import Path

import httpx
import pytest

from bourse_jev.adaptateurs.calendrier_xnys import CalendrierXNYS
from bourse_jev.adaptateurs.horloge import HorlogeSysteme
from bourse_jev.adaptateurs.twelve_data import SourceTwelveData
from bourse_jev.domaine.erreurs import QuotaAtteint, SourceIndisponible
from bourse_jev.domaine.temps import jour_de_marche_courant

FIX = Path(__file__).parents[1] / "fixtures" / "twelve_data"


def source_avec(nom_fixture, statut_http=200, attentes=None, requetes=None):
    corps = json.loads((FIX / nom_fixture).read_text())

    def repondre(requete):
        if requetes is not None:
            requetes.append(requete)
        return httpx.Response(statut_http, json=corps)

    client = httpx.Client(transport=httpx.MockTransport(repondre))
    # `attentes or []` perdrait une liste vide passée par le test : comparaison explicite à None.
    attentes = attentes if attentes is not None else []
    return SourceTwelveData("cle", client=client, attendre=attentes.append, horloge_s=lambda: 0.0)


def test_cours_du_jour_present():
    cours = source_avec("time_series_aapl.json").cours_du_jour("AAPL", date(2026, 10, 27))
    assert cours.cloture == D("232.95") and cours.volume == 48210500
    assert cours.jour == date(2026, 10, 27)


def test_jour_absent_renvoie_none_sans_prendre_la_veille():
    source = source_avec("time_series_aapl.json")
    assert source.cours_du_jour("AAPL", date(2026, 10, 28)) is None


def test_parametres_envoyes():
    requetes = []
    source_avec("time_series_aapl.json", requetes=requetes).cours_du_jour(
        "AAPL", date(2026, 10, 27)
    )
    params = requetes[0].url.params
    assert params["symbol"] == "AAPL" and params["interval"] == "1day"
    assert params["adjust"] == "none"


def test_cle_api_jamais_dans_l_url():
    requetes = []
    source_avec("time_series_aapl.json", requetes=requetes).cours_du_jour(
        "AAPL", date(2026, 10, 27)
    )
    assert "cle" not in str(requetes[0].url)
    assert requetes[0].headers["Authorization"] == "apikey cle"


def test_erreur_429_leve_quota_atteint():
    with pytest.raises(QuotaAtteint):
        source_avec("erreur_429.json").cours_du_jour("AAPL", date(2026, 10, 27))


def test_reponse_erreur_metier_leve_source_indisponible():
    with pytest.raises(SourceIndisponible, match="ZZZZ"):
        source_avec("erreur_symbole.json").cours_du_jour("ZZZZ", date(2026, 10, 27))


def test_reponse_malformee_leve_source_indisponible():
    with pytest.raises(SourceIndisponible):
        source_avec("malformee.json").cours_du_jour("AAPL", date(2026, 10, 27))


def test_reponse_non_json_decrite_sans_la_cle():
    # Cas réel du 28/10/2026 : HTTP 400 au corps non JSON, message d'erreur muet.
    def repondre(requete):
        return httpx.Response(400, text="Bad Request: secret-123 refused\n")

    client = httpx.Client(transport=httpx.MockTransport(repondre))
    source = SourceTwelveData(
        "secret-123", client=client, attendre=[].append, horloge_s=lambda: 0.0
    )
    with pytest.raises(SourceIndisponible) as erreur:
        source.cours_du_jour("AAPL", date(2026, 10, 27))
    message = str(erreur.value)
    assert "HTTP 400" in message and "Bad Request" in message
    assert "secret-123" not in message


def test_quota_journalier_interne_respecte():
    source = source_avec("time_series_aapl.json")
    source.credits_par_jour = 2
    source.cours_du_jour("AAPL", date(2026, 10, 27))
    source.cours_du_jour("AAPL", date(2026, 10, 27))
    with pytest.raises(QuotaAtteint):
        source.cours_du_jour("AAPL", date(2026, 10, 27))
    assert source.credits_consommes == 2


def test_neuvieme_appel_de_la_minute_attend():
    attentes = []
    source = source_avec("time_series_aapl.json", attentes=attentes)
    for _ in range(9):
        source.cours_du_jour("AAPL", date(2026, 10, 27))
    assert len(attentes) == 1 and attentes[0] > 0


@pytest.mark.reel
def test_contrat_reel_twelve_data():
    """Appel réel, exclu par défaut : `uv run pytest -m reel` avec TWELVE_DATA_API_KEY défini."""
    cle = os.environ.get("TWELVE_DATA_API_KEY")
    if not cle:
        pytest.skip("TWELVE_DATA_API_KEY absent")
    aujourd_hui = jour_de_marche_courant(HorlogeSysteme().maintenant())
    # Dernière séance close : la veille au plus tard, pour que la barre soit définitive.
    jour = CalendrierXNYS().jours_de_bourse(aujourd_hui - timedelta(days=10), aujourd_hui)[-2]
    cours = SourceTwelveData(cle).cours_du_jour("AAPL", jour)
    assert cours is not None and cours.jour == jour
    assert 0 < cours.bas <= min(cours.ouverture, cours.cloture)
    assert max(cours.ouverture, cours.cloture) <= cours.haut
    assert cours.volume > 0
