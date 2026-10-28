import pytest

from bourse_jev.config import charger_configuration
from bourse_jev.domaine.erreurs import ConfigurationIncomplete


def test_configuration_complete():
    conf = charger_configuration({"DATABASE_URL": "postgresql://x", "TWELVE_DATA_API_KEY": "cle"})
    assert conf.database_url == "postgresql://x"
    assert conf.twelve_data_api_key == "cle"


def test_variables_manquantes_toutes_nommees():
    with pytest.raises(ConfigurationIncomplete) as erreur:
        charger_configuration({})
    assert "DATABASE_URL" in str(erreur.value)
    assert "TWELVE_DATA_API_KEY" in str(erreur.value)


def test_variable_vide_consideree_manquante():
    with pytest.raises(ConfigurationIncomplete):
        charger_configuration({"DATABASE_URL": "postgresql://x", "TWELVE_DATA_API_KEY": "  "})


def test_le_message_ne_contient_jamais_de_valeur_secrete():
    with pytest.raises(ConfigurationIncomplete) as erreur:
        charger_configuration({"TWELVE_DATA_API_KEY": "secret-123"})
    assert "secret-123" not in str(erreur.value)
