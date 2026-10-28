"""Calendrier des séances de la bourse de New York (NYSE, code ISO XNYS)."""

from datetime import date
from functools import cache
from typing import Any

import exchange_calendars as xcals


@cache
def _calendrier_xnys() -> Any:
    # La construction coûte une à deux secondes : on la partage entre les instances.
    return xcals.get_calendar("XNYS")


class CalendrierXNYS:
    def jours_de_bourse(self, debut: date, fin: date) -> list[date]:
        sessions = _calendrier_xnys().sessions_in_range(debut.isoformat(), fin.isoformat())
        return [s.date() for s in sessions]
