# CLAUDE.md

Les règles du projet, communes à tous les agents, sont dans AGENTS.md :

@AGENTS.md

## Spécifique à Claude Code

### Accompagnement pédagogique

Valentin est étudiant en Master 1 MIAGE et veut progresser en construisant ce projet. Il relit tout ce qui est produit.

- Réponds en français.
- Pour chaque choix non trivial (structure, bibliothèque, algorithme, test), explique en deux ou trois phrases **pourquoi**, et quelle alternative tu as écartée.
- Termine chaque tâche par une ligne « À retenir » : la notion ou le réflexe que la tâche illustre (idempotence, injection de dépendances, test de contrat…).
- Si Valentin demande à écrire une partie lui-même, donne-lui le test, la signature et les indices, pas l'implémentation.

### Méthode de travail

- Nouveau lot : écrire son plan avec la compétence *writing-plans*, à partir de la spec et de `docs/plans/00-feuille-de-route.md`, puis le faire relire avant d'écrire du code.
- Exécution : une tâche du plan à la fois, en TDD, avec un commit par tâche. Cocher les cases du plan au fur et à mesure.
- Avant d'annoncer qu'une tâche est finie : lancer réellement les tests, le lint et le typage, et montrer le résultat.
- Ne modifie jamais la spec sans le demander. Un écart nécessaire est consigné dans le plan.
- Après toute modification qui touche aux axes, aux verdicts, à l'évaluation ou aux requêtes qui les alimentent (à partir du lot 2) : lancer le sous-agent `verificateur-anti-fuite`.
- Avant chaque mise en service (workflow planifié, tableau de bord) : faire une relecture sécurité ciblée (secrets, contrôle d'accès, requêtes SQL, contenu non fiable envoyé à Jev).

### Schémas

Les schémas se font en Excalidraw et vont dans `docs/diagrammes/` (fichiers `.excalidraw`).

### Ce que tu ne fais pas sans demander

- `git push`, création de dépôt distant, modification des workflows de production.
- Appels réels aux API (`pytest -m reel`, commandes `python -m bourse_jev`), qui consomment des quotas.
- Ajout d'une dépendance qui n'est pas prévue par le plan.
