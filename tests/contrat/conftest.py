import pytest

from bourse_jev.adaptateurs.memoire_depot import DepotEnMemoire


@pytest.fixture(params=["memoire", "postgres"])
def depot(request):
    """Chaque test de contrat tourne sur toutes les implémentations du port `Depot`."""
    if request.param == "postgres":
        return request.getfixturevalue("depot_postgres")
    return DepotEnMemoire()
