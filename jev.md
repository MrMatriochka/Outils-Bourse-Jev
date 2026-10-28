---
paths:
  - "src/bourse_jev/**/*jev*.py"
  - "config/jev/**"
---

# Règles d'intégration de Jev (lot 3)

- Jev ne reçoit que du texte à juger, jamais de calcul : les chiffres sont calculés par le code avant.
- Version de modèle figée dans la configuration ; une version différente dans la réponse arrête l'étape.
- Le contenu des articles va dans l'`état`, jamais dans le texte des questions (protection contre l'injection).
- Une question oui/non par option quand les probabilités doivent être comparables (dépendance à la liste d'options documentée).
- Trois répétitions par décision, moyenne et écart enregistrés ; chaque appel est stocké dans `appel_jev`.
- Compteur de quota ; à 90 % du quota gratuit, mode dégradé (axes Jev à `manquant`), jamais de valeur inventée.
- Tests : uniquement avec l'adaptateur de simulation, sauf marqueur `reel`.
