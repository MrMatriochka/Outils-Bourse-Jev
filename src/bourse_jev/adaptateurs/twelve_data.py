"""Source de cours Twelve Data (offre Basic : 8 crédits par minute, 800 par jour)."""

import time
from collections import deque
from collections.abc import Callable
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from bourse_jev.domaine.erreurs import QuotaAtteint, SourceIndisponible
from bourse_jev.domaine.modeles import CoursBrut

URL_TIME_SERIES = "https://api.twelvedata.com/time_series"
# 30 barres couvrent la fenêtre de rattrapage (10 jours de bourse) pour le même crédit.
NB_BARRES = 30
FENETRE_S = 60.0


class SourceTwelveData:
    nom = "twelve_data"

    def __init__(
        self,
        cle_api: str,
        client: httpx.Client | None = None,
        credits_par_minute: int = 8,
        credits_par_jour: int = 800,
        attendre: Callable[[float], None] = time.sleep,
        horloge_s: Callable[[], float] = time.monotonic,
    ) -> None:
        self._cle_api = cle_api
        self._client = client or httpx.Client(timeout=30.0)
        self.credits_par_minute = credits_par_minute
        self.credits_par_jour = credits_par_jour
        self._attendre = attendre
        self._horloge_s = horloge_s
        self._appels: deque[float] = deque()
        self.credits_consommes = 0

    def cours_du_jour(self, symbole: str, jour: date) -> CoursBrut | None:
        if self.credits_consommes >= self.credits_par_jour:
            raise QuotaAtteint(f"quota interne de {self.credits_par_jour} crédits par jour atteint")
        self._respecter_le_debit()
        corps = self._appeler(symbole)
        for barre in corps.get("values") or []:
            if barre.get("datetime") == jour.isoformat():
                return _convertir(symbole, jour, barre)
        # Jour absent : jamais de repli sur la barre de la veille.
        return None

    def _respecter_le_debit(self) -> None:
        """Fenêtre glissante d'une minute : au plus `credits_par_minute` appels."""
        maintenant = self._horloge_s()
        while self._appels and maintenant - self._appels[0] >= FENETRE_S:
            self._appels.popleft()
        if len(self._appels) >= self.credits_par_minute:
            self._attendre(FENETRE_S - (maintenant - self._appels[0]))
            self._appels.popleft()
            maintenant = self._horloge_s()
        self._appels.append(maintenant)

    def _appeler(self, symbole: str) -> dict[str, Any]:
        try:
            reponse = self._client.get(
                URL_TIME_SERIES,
                params={
                    "symbol": symbole,
                    "interval": "1day",
                    "outputsize": NB_BARRES,
                    "adjust": "none",
                },
                # Clé en en-tête plutôt qu'en paramètre : elle n'apparaît ni dans l'URL ni
                # dans les messages d'erreur d'httpx.
                headers={"Authorization": f"apikey {self._cle_api}"},
            )
        except httpx.HTTPError as erreur:
            raise SourceIndisponible(
                f"{symbole} : erreur réseau ({type(erreur).__name__})"
            ) from None
        self.credits_consommes += 1
        try:
            corps = reponse.json()
        except ValueError:
            corps = None
        code = corps.get("code") if isinstance(corps, dict) else None
        if reponse.status_code == 429 or code == 429:
            raise QuotaAtteint(f"{symbole} : quota Twelve Data atteint (429)")
        if not isinstance(corps, dict):
            raise SourceIndisponible(
                f"{symbole} : réponse illisible (HTTP {reponse.status_code}, "
                f"{self._extrait(reponse.text)!r})"
            )
        if reponse.status_code != 200 or corps.get("status") != "ok":
            message = str(corps.get("message", "erreur sans message"))[:200]
            raise SourceIndisponible(
                f"{symbole} : erreur {code or reponse.status_code} ({message})"
            )
        return corps

    def _extrait(self, texte: str) -> str:
        """Début du corps de réponse, sur une ligne et sans la clé, pour diagnostiquer."""
        return " ".join(texte.replace(self._cle_api, "<CLE>").split())[:120]


def _convertir(symbole: str, jour: date, barre: dict[str, Any]) -> CoursBrut:
    try:
        return CoursBrut(
            jour=jour,
            ouverture=Decimal(barre["open"]),
            haut=Decimal(barre["high"]),
            bas=Decimal(barre["low"]),
            cloture=Decimal(barre["close"]),
            volume=int(barre["volume"]),
        )
    except (KeyError, TypeError, ValueError, InvalidOperation) as erreur:
        raise SourceIndisponible(
            f"{symbole} : barre du {jour.isoformat()} malformée ({type(erreur).__name__})"
        ) from None
