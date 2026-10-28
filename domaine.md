---
paths:
  - "src/bourse_jev/domaine/**/*.py"
---

# Règles du domaine

- Aucune entrée/sortie : pas d'import de `httpx`, `psycopg`, `exchange_calendars`, `os.environ`, ni d'appel à `datetime.now()` ou `date.today()`. Le temps arrive par le port `Horloge` ou en paramètre.
- Les dépendances vers l'extérieur sont des `typing.Protocol` dans `ports.py`, jamais des classes concrètes.
- Modèles en `dataclass(frozen=True)`, montants en `Decimal`, jamais en `float`.
- Une fonction du domaine est déterministe : même entrée, même sortie. C'est ce qui la rend testable sans doublure.
