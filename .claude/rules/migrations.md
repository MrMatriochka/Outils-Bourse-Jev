---
paths:
  - "migrations/**/*.sql"
  - "src/bourse_jev/adaptateurs/postgres*.py"
---

# Règles SQL et migrations

- Une migration déjà appliquée n'est jamais modifiée : toute évolution passe par un nouveau fichier numéroté (`002_…sql`).
- Les tables de faits sont en ajout seul : un déclencheur refuse `UPDATE` et `DELETE`. Seule la table `execution` (journal technique) se met à jour.
- Clés naturelles composées et `ON CONFLICT … DO NOTHING` pour l'idempotence.
- Toujours des requêtes paramétrées (`%s` avec psycopg), jamais de chaîne SQL construite avec des valeurs.
- Chaque donnée externe a une colonne `recupere_le timestamptz not null`.
