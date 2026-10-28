"""Horloge réelle du système."""

from datetime import UTC, datetime


class HorlogeSysteme:
    def maintenant(self) -> datetime:
        return datetime.now(UTC)
