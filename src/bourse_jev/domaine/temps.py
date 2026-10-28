"""Règles de temps du marché américain."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

NEW_YORK = ZoneInfo("America/New_York")


def jour_de_marche_courant(maintenant: datetime) -> date:
    """Date du jour à New York : une exécution à 2 h à Paris tombe encore la veille."""
    return maintenant.astimezone(NEW_YORK).date()
