"""Contrôles de vraisemblance d'un cours avant stockage."""

from decimal import Decimal
from enum import StrEnum

from bourse_jev.domaine.modeles import CoursJournalier

VARIATION_MAXIMALE = Decimal("0.5")


class MotifRejet(StrEnum):
    VALEUR_NON_POSITIVE = "valeur_non_positive"
    INCOHERENCE_HAUT_BAS = "incoherence_haut_bas"
    VARIATION_ABERRANTE = "variation_aberrante"


def valider_cours(
    cours: CoursJournalier, cloture_precedente: Decimal | None
) -> MotifRejet | None:
    """Renvoie le premier motif de rejet trouvé, ou `None` si le cours est vraisemblable.

    Une variation de 50 % exactement est acceptée ; seule une variation strictement
    supérieure est jugée aberrante.
    """
    prix = (cours.ouverture, cours.haut, cours.bas, cours.cloture)
    if any(p <= 0 for p in prix) or cours.volume < 0:
        return MotifRejet.VALEUR_NON_POSITIVE
    if cours.haut < max(cours.ouverture, cours.cloture, cours.bas) or cours.bas > min(
        cours.ouverture, cours.cloture
    ):
        return MotifRejet.INCOHERENCE_HAUT_BAS
    if cloture_precedente is not None and cloture_precedente > 0:
        if abs(cours.cloture / cloture_precedente - 1) > VARIATION_MAXIMALE:
            return MotifRejet.VARIATION_ABERRANTE
    return None
