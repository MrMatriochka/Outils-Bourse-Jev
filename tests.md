---
paths:
  - "tests/**/*.py"
---

# Règles des tests

- Nom de test en français, qui décrit un comportement : `test_cours_absent_n_est_pas_remplace_par_la_veille`.
- Les valeurs attendues viennent de la spec ou du plan, écrites en dur dans le test, jamais recalculées avec le code testé.
- Aucun appel réseau hors marqueur `@pytest.mark.reel`. Les API sont simulées par `httpx.MockTransport` et des fixtures JSON dans `tests/fixtures/`.
- Aucune attente réelle : injecter `attendre` et l'horloge (`HorlogeFixe`).
- Doublures partagées dans `tests/doublures.py` ; une suite de contrat (`tests/contrat/`) se passe sur toutes les implémentations d'un port.
- Ne jamais affaiblir un test pour le faire passer : corriger le code, ou signaler l'écart avec la spec.
