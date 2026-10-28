import pytest

from bourse_jev.adaptateurs.memoire_depot import DepotEnMemoire


@pytest.fixture(params=["memoire"])
def depot(request):
    """Chaque test de contrat tourne sur toutes les implémentations du port `Depot`."""
    return DepotEnMemoire()
