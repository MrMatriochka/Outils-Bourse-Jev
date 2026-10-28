# Outil bourse JEV

Un outil d'analyse boursière quotidienne, conçu d'abord pour **mesurer honnêtement** ce qu'il vaut.

Chaque jour de bourse américain, il collecte les cours et les actualités d'actions américaines, calcule des axes d'analyse, et produit pour trois horizons (1 semaine, 1 mois, 3 mois) un verdict *monter / stable / descendre*, avec sa confiance et un profil de risque. Le modèle de décision [Jev](https://typesafe.ai) (TypeSafe AI) lit les actualités ; tous les calculs sont faits par du code classique.

> **Avertissement.** Projet personnel à visée pédagogique. Les analyses produites ne constituent pas un conseil en investissement. L'outil ne passe aucun ordre et n'est connecté à aucun courtier.

## Ce qui rend le projet intéressant

- **Jev comme capteur, pas comme juge.** Jev transforme le texte des actualités en valeurs typées (tonalité, importance, risque d'événement). Il ne fait aucun calcul, sa version est figée et chaque appel est tracé.
- **Champion / challenger.** Une grille de règles produit les verdicts au départ, une régression logistique la remplace par horizon quand assez de résultats sont disponibles, et un arbitre Jev tourne dans l'ombre pour comparaison.
- **Évaluation sans tricherie.** Test en avant uniquement pour les axes Jev (un modèle de langage « connaît » déjà le passé), comparaison systématique à des références naïves, correction des fenêtres chevauchantes, panel témoin contre le biais de sélection.
- **Données traçables.** Ajout seul et horodatage de connaissance : chaque verdict peut être rejoué avec exactement ce que l'outil savait ce jour-là.
- **0 € par mois.** GitHub Actions, Postgres sur Neon, Streamlit Community Cloud, offres gratuites de Twelve Data, Finnhub et Cloudflare Workers AI.

## Architecture

Architecture hexagonale en Python : un domaine sans entrée/sortie, des ports, des adaptateurs interchangeables pour chaque source. Schémas dans `docs/diagrammes/` (à ouvrir avec [Excalidraw](https://excalidraw.com)).

## Avancement

| Lot | Contenu | État |
| --- | --- | --- |
| 1 | Socle de données : collecte quotidienne, idempotence, rattrapage | À démarrer |
| 2 | Axes de code et grille de règles | À venir |
| 3 | Intégration de Jev | À venir |
| 4 | Tableau de bord | À venir |
| 5 | Évaluation et modèle appris | À venir |

## Documentation

- Spec : `docs/specs/2026-10-28-outil-bourse-jev-design.md`
- Feuille de route : `docs/plans/00-feuille-de-route.md`
- Décisions d'architecture : `docs/decisions.md`
- Règles pour les agents de code : `AGENTS.md`

## Démarrer en local

```bash
cp .env.example .env        # puis remplir
uv sync
uv run pytest
```
