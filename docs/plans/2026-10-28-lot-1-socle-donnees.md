# Lot 1 — Socle de données : plan d'implémentation

> **Pour les agents :** sous-compétence REQUISE : utiliser superpowers:subagent-driven-development (recommandé) ou superpowers:executing-plans pour exécuter ce plan tâche par tâche. Les étapes utilisent des cases à cocher (`- [ ]`) pour le suivi.

**Objectif :** collecter chaque jour de bourse américain, sans intervention, les cours de clôture du panel témoin et de l'ETF de référence dans une base Postgres, de façon idempotente et avec rattrapage des jours manqués.

**Architecture :** architecture hexagonale. Le domaine (`domaine/`) définit les modèles, la validation des cours et les ports (interfaces `Protocol`) ; le cas d'usage `collecter` (`application/`) orchestre ; les adaptateurs (`adaptateurs/`) branchent Twelve Data, Postgres, le calendrier NYSE et l'horloge. Un `DepotEnMemoire` et des sources factices permettent de tester le domaine et l'application sans réseau.

**Pile technique :** Python 3.12, uv, httpx, psycopg 3, exchange_calendars, pytest, ruff, mypy, GitHub Actions, Postgres (Neon en production, conteneur en CI).

**Spec :** `docs/specs/2026-10-28-outil-bourse-jev-design.md` (sections 5, 6, 10, 11, 12 et 13 lot 1).

## Contraintes globales

- Aucun module, aucune dépendance et aucune clé de courtier dans le dépôt.
- Aucun secret dans le code : configuration par variables d'environnement uniquement (`DATABASE_URL`, `TWELVE_DATA_API_KEY`).
- Ajout seul sur `cours_journalier` : jamais d'`UPDATE` ni de `DELETE` ; une ligne déjà présente n'est jamais écrasée.
- Horodatage de connaissance : chaque cours stocké porte `recupere_le` (UTC), fourni par le port `Horloge`.
- Idempotence : relancer `collecter` le même jour ne crée aucun doublon (clé `(titre_id, jour)`).
- Rattrapage : les jours de bourse sans exécution réussie, dans la limite des **10 derniers jours de bourse**, sont traités du plus ancien au plus récent.
- Twelve Data : **8 crédits par minute, 800 par jour**, 1 crédit par appel `time_series`, cours bruts (`adjust=none`).
- Cours rejeté si clôture, ouverture, haut ou bas ≤ 0, volume < 0, haut < bas (ou incohérent avec ouverture/clôture), ou variation de clôture **strictement supérieure à 50 %** par rapport à la clôture précédente.
- Un cours absent pour le jour demandé n'est jamais remplacé par celui de la veille.
- Base en veille (Neon) : **une** nouvelle tentative de connexion après **5 secondes**.
- Le « jour de marché courant » se calcule dans le fuseau **America/New_York**.
- Requêtes SQL paramétrées uniquement.
- Identifiants Python en français sans accents (`cloture`, `recupere_le`), commentaires et docstrings en français, messages de commit en français au format conventionnel (`feat(collecte): …`).
- Écarts assumés par rapport à la spec, section 6 : la colonne `cloture_ajustee` n'est pas créée au lot 1 (question des dividendes et divisions reportée au lot 2, voir la feuille de route) ; la table `titre` reçoit une colonne `est_reference` pour repérer l'ETF S&P 500 (SPY).

## Points d'attention (Review Focus)

1. **Fuseau horaire** : une exécution manuelle à 2 h du matin à Paris tombe encore la veille à New York ; le jour collecté doit être celui de New York. → test `test_jour_de_marche_courant_utilise_new_york` (tâche 3).
2. **Jours de clôture anticipée** (lendemain de Thanksgiving, 27/11/2026) : ce sont des jours de bourse normaux. → assertion dans `test_semaine_de_thanksgiving_2026` (tâche 4).
3. **Symbole inconnu ou erreur métier de l'API** (réponse `status: error`, code 400/404) : erreur sur ce titre seulement, la journée continue. → `test_reponse_erreur_metier_leve_source_indisponible` (tâche 7) et `test_erreur_sur_un_titre_n_arrete_pas_les_autres` (tâche 9).
4. **Réponse d'API malformée** (champ manquant, valeur non numérique) : erreur explicite, jamais un cours partiellement rempli. → `test_reponse_malformee_leve_source_indisponible` (tâche 7).
5. **Base Neon en veille** au démarrage du batch : une nouvelle tentative, puis échec clair. → `test_connecter_reessaie_une_fois_apres_5_secondes` (tâche 6).

---

## Structure des fichiers

```
pyproject.toml                         dépendances, ruff, mypy, pytest
.python-version                        3.12
.github/workflows/tests.yml            CI : lint, typage, tests (Postgres en service)
.github/workflows/collecte.yml         batch planifié + déclenchement manuel
config/panel_temoin.csv                30 titres + ETF de référence
migrations/001_socle.sql               tables titre, cours_journalier, execution
src/bourse_jev/
  __init__.py                          __version__
  __main__.py                          CLI : migrer | catalogue | collecter
  config.py                            Configuration, charger_configuration
  domaine/
    modeles.py                         Titre, CoursBrut, CoursJournalier, enums, RapportExecution
    validation.py                      MotifRejet, valider_cours
    ports.py                           SourceDeCours, Depot, CalendrierDeMarche, Horloge
    erreurs.py                         QuotaAtteint, SourceIndisponible, ConfigurationIncomplete
    temps.py                           jour_de_marche_courant
  application/
    catalogue.py                       charger_panel, synchroniser_catalogue
    collecte.py                        collecter
  adaptateurs/
    horloge.py                         HorlogeSysteme
    calendrier_xnys.py                 CalendrierXNYS
    memoire_depot.py                   DepotEnMemoire
    postgres.py                        connecter, appliquer_migrations, DepotPostgres
    twelve_data.py                     SourceTwelveData
tests/
  conftest.py                          fixtures pytest (base de test, dépôts)
  doublures.py                         HorlogeFixe, fabriquer_cours, SourceFactice, CalendrierFactice
  fixtures/twelve_data/*.json          réponses d'API écrites à la main
  domaine/  application/  adaptateurs/  contrat/
```

---

### Tâche 1 : socle du projet et intégration continue

**Fichiers :**
- Créer : `pyproject.toml`, `.python-version`, `src/bourse_jev/__init__.py`, `.github/workflows/tests.yml`
- Test : `tests/test_socle.py`

**Interfaces :**
- Produit : le paquet installable `bourse_jev` ; `bourse_jev.__version__: str` ; les commandes `uv run pytest`, `uv run ruff check .`, `uv run mypy src`.

- [x] **Étape 1 : écrire le test qui échoue**

```python
import bourse_jev

def test_le_paquet_expose_sa_version():
    assert bourse_jev.__version__ == "0.1.0"
```

- [x] **Étape 2 : lancer le test et vérifier l'échec**

Commande : `uv run pytest tests/test_socle.py -v` — attendu : échec (`ModuleNotFoundError`).

- [x] **Étape 3 : créer `pyproject.toml` et le paquet**

Projet `bourse-jev` version `0.1.0`, `requires-python = ">=3.12"`, disposition `src/`, paquet `bourse_jev`. Dépendances : `httpx`, `psycopg[binary]`, `exchange_calendars`. Dépendances de développement : `pytest`, `ruff`, `mypy`. Ruff : `line-length = 100`, règles `E,F,I,B,UP`. Mypy : `strict = true` sur `src`. Pytest : `pythonpath = ["."]` (pour importer `tests.doublures`), marqueur `reel` (« appelle une vraie API, exclu par défaut ») et `addopts = "-m 'not reel'"`. Créer `tests/__init__.py` vide.

- [x] **Étape 4 : écrire `.github/workflows/tests.yml`**

Déclenché sur `push` et `pull_request`. Un service `postgres:16` (utilisateur, mot de passe et base `test`, port 5432, contrôle de santé `pg_isready`). Étapes : récupérer le code, installer uv, `uv sync`, `uv run ruff check .`, `uv run mypy src`, `uv run pytest`, avec `TEST_DATABASE_URL=postgresql://test:test@localhost:5432/test`.

- [x] **Étape 5 : vérifier**

Commandes : `uv run pytest -v`, `uv run ruff check .`, `uv run mypy src` — attendu : tout passe.

- [x] **Étape 6 : commit**

```bash
git add pyproject.toml .python-version src/ tests/ .github/workflows/tests.yml uv.lock
git commit -m "chore: socle du projet Python et intégration continue"
```

---

### Tâche 2 : configuration

**Fichiers :**
- Créer : `src/bourse_jev/config.py`, `src/bourse_jev/domaine/erreurs.py`
- Test : `tests/test_config.py`

**Interfaces :**
- Produit : `Configuration(database_url: str, twelve_data_api_key: str)` (dataclass figée) ; `charger_configuration(env: Mapping[str, str] = os.environ) -> Configuration` ; `ConfigurationIncomplete(Exception)` dont le message liste les variables manquantes, sans jamais afficher de valeur.

- [x] **Étape 1 : écrire les tests qui échouent**

```python
import pytest
from bourse_jev.config import charger_configuration
from bourse_jev.domaine.erreurs import ConfigurationIncomplete

def test_configuration_complete():
    conf = charger_configuration({"DATABASE_URL": "postgresql://x", "TWELVE_DATA_API_KEY": "cle"})
    assert conf.database_url == "postgresql://x"
    assert conf.twelve_data_api_key == "cle"

def test_variables_manquantes_toutes_nommees():
    with pytest.raises(ConfigurationIncomplete) as erreur:
        charger_configuration({})
    assert "DATABASE_URL" in str(erreur.value)
    assert "TWELVE_DATA_API_KEY" in str(erreur.value)

def test_variable_vide_consideree_manquante():
    with pytest.raises(ConfigurationIncomplete):
        charger_configuration({"DATABASE_URL": "postgresql://x", "TWELVE_DATA_API_KEY": "  "})

def test_le_message_ne_contient_jamais_de_valeur_secrete():
    with pytest.raises(ConfigurationIncomplete) as erreur:
        charger_configuration({"TWELVE_DATA_API_KEY": "secret-123"})
    assert "secret-123" not in str(erreur.value)
```

- [x] **Étape 2 : vérifier l'échec** — `uv run pytest tests/test_config.py -v`
- [x] **Étape 3 : implémenter `charger_configuration` et `ConfigurationIncomplete`** (créer aussi dans `erreurs.py` : `QuotaAtteint(Exception)` et `SourceIndisponible(Exception)`, utilisées aux tâches 7 et 9).
- [x] **Étape 4 : vérifier** — `uv run pytest tests/test_config.py -v` passe.
- [x] **Étape 5 : commit** — `feat(config): chargement de la configuration par variables d'environnement`

---

### Tâche 3 : modèles du domaine, validation des cours et ports

**Fichiers :**
- Créer : `src/bourse_jev/domaine/modeles.py`, `validation.py`, `ports.py`, `temps.py`, `src/bourse_jev/adaptateurs/horloge.py`, `tests/doublures.py`
- Test : `tests/domaine/test_validation.py`, `tests/domaine/test_temps.py`

**Interfaces :**
- Produit, dans `modeles.py` (dataclasses figées, montants en `Decimal`) :
  - `Titre(id: int | None, symbole: str, place: str, nom: str, devise: str, actif: bool, panel_temoin: bool, est_reference: bool)`
  - `CoursBrut(jour: date, ouverture: Decimal, haut: Decimal, bas: Decimal, cloture: Decimal, volume: int)` — ce que renvoie une source
  - `CoursJournalier(titre_id: int, jour: date, ouverture: Decimal, haut: Decimal, bas: Decimal, cloture: Decimal, volume: int, source: str, recupere_le: datetime)` — ce qui est stocké
  - `StatutExecution(StrEnum)` : `EN_COURS`, `OK`, `PARTIELLE`, `SANS_OBJET`, `ECHEC` (valeurs en minuscules : `"en_cours"`, `"ok"`…, identiques aux contraintes SQL de la tâche 6)
  - `Declencheur(StrEnum)` : `CRON`, `MANUEL`, `RATTRAPAGE` (valeurs `"cron"`, `"manuel"`, `"rattrapage"`)
  - `RapportExecution(date_marche: date, statut: StatutExecution, nb_cours_enregistres: int, erreurs: list[str], titres_en_retard: list[str], credits_consommes: int)`
- Produit, dans `validation.py` : `MotifRejet(StrEnum)` : `VALEUR_NON_POSITIVE`, `INCOHERENCE_HAUT_BAS`, `VARIATION_ABERRANTE` (valeurs en minuscules, par exemple `"variation_aberrante"`) ; `valider_cours(cours: CoursJournalier, cloture_precedente: Decimal | None) -> MotifRejet | None`.
- Produit, dans `ports.py` (`typing.Protocol`) :
  - `Horloge.maintenant() -> datetime` (UTC, avec fuseau)
  - `CalendrierDeMarche.jours_de_bourse(debut: date, fin: date) -> list[date]` (bornes incluses, ordre croissant)
  - `SourceDeCours.nom: str` ; `SourceDeCours.cours_du_jour(symbole: str, jour: date) -> CoursBrut | None` (lève `QuotaAtteint` ou `SourceIndisponible`) ; `SourceDeCours.credits_consommes: int`
  - `Depot` : `enregistrer_titres(titres: list[Titre]) -> int` ; `titres_a_collecter() -> list[Titre]` ; `cloture_precedente(titre_id: int, avant: date) -> Decimal | None` ; `enregistrer_cours(cours: CoursJournalier) -> bool` (vrai si insérée, faux si déjà présente) ; `dates_reussies(depuis: date) -> set[date]` ; `debuter_execution(date_marche: date, declencheur: Declencheur, debut: datetime) -> int` ; `terminer_execution(execution_id: int, rapport: RapportExecution, fin: datetime) -> None`
- Produit, dans `temps.py` : `jour_de_marche_courant(maintenant: datetime) -> date` (date dans `America/New_York`).
- Produit, dans `adaptateurs/horloge.py` : `HorlogeSysteme` ; dans `tests/doublures.py` : `HorlogeFixe(instant: datetime)` et une fabrique `fabriquer_cours(**modifs) -> CoursJournalier` (titre 1, 27/10/2026, OHLC 100/101/99/100, volume 1000, source `"test"`, `recupere_le` 27/10/2026 21 h 45 UTC ; chaque argument nommé remplace le champ du même nom).

- [x] **Étape 1 : écrire les tests qui échouent**

```python
from decimal import Decimal as D
from bourse_jev.domaine.validation import MotifRejet, valider_cours
from tests.doublures import fabriquer_cours

def test_cours_normal_accepte():
    assert valider_cours(fabriquer_cours(), cloture_precedente=D("98")) is None

def test_premier_cours_sans_precedent_accepte():
    assert valider_cours(fabriquer_cours(), cloture_precedente=None) is None

def test_cloture_nulle_rejetee():
    c = fabriquer_cours(cloture=D("0"), bas=D("0"))
    assert valider_cours(c, D("98")) is MotifRejet.VALEUR_NON_POSITIVE

def test_volume_negatif_rejete():
    assert valider_cours(fabriquer_cours(volume=-1), D("98")) is MotifRejet.VALEUR_NON_POSITIVE

def test_haut_inferieur_au_bas_rejete():
    c = fabriquer_cours(haut=D("98"), bas=D("99"))
    assert valider_cours(c, D("98")) is MotifRejet.INCOHERENCE_HAUT_BAS

def test_cloture_au_dessus_du_haut_rejetee():
    c = fabriquer_cours(cloture=D("102"))
    assert valider_cours(c, D("98")) is MotifRejet.INCOHERENCE_HAUT_BAS

def test_hausse_de_50_pourcent_exactement_acceptee():
    c = fabriquer_cours(ouverture=D("150"), haut=D("150"), bas=D("149"), cloture=D("150"))
    assert valider_cours(c, D("100")) is None

def test_hausse_superieure_a_50_pourcent_rejetee():
    c = fabriquer_cours(ouverture=D("151"), haut=D("151"), bas=D("150"), cloture=D("151"))
    assert valider_cours(c, D("100")) is MotifRejet.VARIATION_ABERRANTE

def test_baisse_superieure_a_50_pourcent_rejetee():
    c = fabriquer_cours(ouverture=D("49"), haut=D("49"), bas=D("48"), cloture=D("49"))
    assert valider_cours(c, D("100")) is MotifRejet.VARIATION_ABERRANTE
```

```python
from datetime import date, datetime, timezone
from bourse_jev.domaine.temps import jour_de_marche_courant

def test_jour_de_marche_courant_utilise_new_york():
    # 29/10/2026 à 3 h 30 UTC = 28/10/2026 à 23 h 30 à New York
    assert jour_de_marche_courant(datetime(2026, 10, 29, 3, 30, tzinfo=timezone.utc)) == date(2026, 10, 28)

def test_jour_de_marche_courant_apres_la_cloture():
    assert jour_de_marche_courant(datetime(2026, 10, 28, 21, 45, tzinfo=timezone.utc)) == date(2026, 10, 28)
```

- [x] **Étape 2 : vérifier l'échec** — `uv run pytest tests/domaine -v`
- [x] **Étape 3 : implémenter les modèles, `valider_cours`, les ports, `jour_de_marche_courant` et `HorlogeSysteme`**

Ordre des contrôles dans `valider_cours` : valeurs non positives, puis cohérence (`haut >= max(ouverture, cloture, bas)` et `bas <= min(ouverture, cloture)`), puis variation `abs(cloture / cloture_precedente - 1) > Decimal("0.5")`. `jour_de_marche_courant` utilise `zoneinfo.ZoneInfo("America/New_York")`.

- [x] **Étape 4 : vérifier** — `uv run pytest tests/domaine -v` passe, `uv run mypy src` passe.
- [x] **Étape 5 : commit** — `feat(domaine): modèles, validation des cours et ports`

---

### Tâche 4 : calendrier de la bourse de New York

**Fichiers :**
- Créer : `src/bourse_jev/adaptateurs/calendrier_xnys.py`
- Test : `tests/adaptateurs/test_calendrier_xnys.py`

**Interfaces :**
- Consomme : le port `CalendrierDeMarche` (tâche 3).
- Produit : `CalendrierXNYS()` qui implémente `jours_de_bourse(debut, fin)` à partir du calendrier `XNYS` d'`exchange_calendars`.

- [x] **Étape 1 : écrire les tests qui échouent**

```python
from datetime import date
from bourse_jev.adaptateurs.calendrier_xnys import CalendrierXNYS

def test_semaine_de_thanksgiving_2026():
    jours = CalendrierXNYS().jours_de_bourse(date(2026, 11, 23), date(2026, 11, 29))
    # 26/11 Thanksgiving fermé ; 27/11 clôture anticipée mais ouvert ; week-end exclu
    assert jours == [date(2026, 11, 23), date(2026, 11, 24), date(2026, 11, 25), date(2026, 11, 27)]

def test_fete_nationale_observee_le_vendredi_3_juillet_2026():
    assert date(2026, 7, 3) not in CalendrierXNYS().jours_de_bourse(date(2026, 6, 29), date(2026, 7, 3))

def test_intervalle_sans_jour_de_bourse():
    assert CalendrierXNYS().jours_de_bourse(date(2026, 10, 31), date(2026, 11, 1)) == []
```

- [x] **Étape 2 : vérifier l'échec** — `uv run pytest tests/adaptateurs/test_calendrier_xnys.py -v`
- [x] **Étape 3 : implémenter `CalendrierXNYS.jours_de_bourse`** (`sessions_in_range`, conversion en `date`).
- [x] **Étape 4 : vérifier** — les trois tests passent.
- [x] **Étape 5 : commit** — `feat(adaptateurs): calendrier de la bourse de New York`

---

### Tâche 5 : dépôt en mémoire et suite de contrat du dépôt

**Fichiers :**
- Créer : `src/bourse_jev/adaptateurs/memoire_depot.py`
- Test : `tests/contrat/test_depot.py`, `tests/contrat/conftest.py`

**Interfaces :**
- Consomme : le port `Depot` et les modèles (tâche 3).
- Produit : `DepotEnMemoire()` ; une fixture pytest `depot` paramétrée sur `["memoire"]`, à laquelle la tâche 6 ajoute `"postgres"`. Les attributs internes du dépôt en mémoire ne sont jamais lus par les tests : seules les méthodes du port le sont, pour que la même suite vaille contrat pour Postgres.

- [x] **Étape 1 : écrire les tests de contrat qui échouent**

```python
from datetime import date, datetime, timezone
from decimal import Decimal as D
from bourse_jev.domaine.modeles import Declencheur, RapportExecution, StatutExecution, Titre
from tests.doublures import fabriquer_cours

DEBUT = datetime(2026, 10, 27, 21, 45, tzinfo=timezone.utc)

def titre(symbole, actif=True, panel=True, reference=False):
    return Titre(None, symbole, "XNYS", symbole, "USD", actif, panel, reference)

def test_enregistrer_titres_est_idempotent(depot):
    assert depot.enregistrer_titres([titre("AAPL"), titre("MSFT")]) == 2
    assert depot.enregistrer_titres([titre("AAPL")]) == 0
    assert sorted(t.symbole for t in depot.titres_a_collecter()) == ["AAPL", "MSFT"]

def test_titres_inactifs_exclus_de_la_collecte(depot):
    depot.enregistrer_titres([titre("AAPL"), titre("OLD", actif=False)])
    assert [t.symbole for t in depot.titres_a_collecter()] == ["AAPL"]

def test_cours_jamais_ecrase(depot):
    depot.enregistrer_titres([titre("AAPL")])
    tid = depot.titres_a_collecter()[0].id
    assert depot.enregistrer_cours(fabriquer_cours(titre_id=tid)) is True
    assert depot.enregistrer_cours(fabriquer_cours(titre_id=tid, cloture=D("100.5"))) is False
    assert depot.cloture_precedente(tid, avant=date(2026, 10, 28)) == D("100")

def test_cloture_precedente_strictement_avant(depot):
    depot.enregistrer_titres([titre("AAPL")])
    tid = depot.titres_a_collecter()[0].id
    depot.enregistrer_cours(fabriquer_cours(titre_id=tid, jour=date(2026, 10, 26), cloture=D("99")))
    depot.enregistrer_cours(fabriquer_cours(titre_id=tid, jour=date(2026, 10, 27), cloture=D("100")))
    assert depot.cloture_precedente(tid, avant=date(2026, 10, 27)) == D("99")
    assert depot.cloture_precedente(tid, avant=date(2026, 10, 26)) is None

def test_execution_relancee_reutilise_la_meme_ligne(depot):
    a = depot.debuter_execution(date(2026, 10, 27), Declencheur.CRON, DEBUT)
    b = depot.debuter_execution(date(2026, 10, 27), Declencheur.MANUEL, DEBUT)
    assert a == b

def test_dates_reussies_ne_contiennent_que_ok_et_sans_objet(depot):
    for jour, statut in [(27, StatutExecution.OK), (26, StatutExecution.PARTIELLE), (25, StatutExecution.SANS_OBJET)]:
        d = date(2026, 10, jour)
        eid = depot.debuter_execution(d, Declencheur.CRON, DEBUT)
        depot.terminer_execution(eid, RapportExecution(d, statut, 0, [], [], 0), DEBUT)
    assert depot.dates_reussies(depuis=date(2026, 10, 1)) == {date(2026, 10, 27), date(2026, 10, 25)}
```

- [x] **Étape 2 : vérifier l'échec** — `uv run pytest tests/contrat -v`
- [x] **Étape 3 : implémenter `DepotEnMemoire`** (identifiants séquentiels à partir de 1, unicité titre sur `(symbole, place)`).
- [x] **Étape 4 : vérifier** — `uv run pytest tests/contrat -v` passe.
- [x] **Étape 5 : commit** — `feat(adaptateurs): dépôt en mémoire et suite de contrat`

---

### Tâche 6 : schéma Postgres, migrations et dépôt Postgres

**Fichiers :**
- Créer : `migrations/001_socle.sql`, `src/bourse_jev/adaptateurs/postgres.py`
- Modifier : `tests/contrat/conftest.py` (ajout du paramètre `"postgres"`)
- Test : `tests/adaptateurs/test_postgres.py`

**Interfaces :**
- Consomme : le port `Depot`, la suite de contrat (tâche 5).
- Produit : `connecter(dsn: str, tentatives: int = 2, delai_s: float = 5.0, attendre: Callable[[float], None] = time.sleep, ouvrir: Callable[[str], psycopg.Connection] = psycopg.connect) -> psycopg.Connection` ; `appliquer_migrations(conn: psycopg.Connection, dossier: Path) -> list[str]` (renvoie les versions appliquées lors de cet appel) ; `DepotPostgres(conn: psycopg.Connection)`.

Contenu de `001_socle.sql` :
- `schema_migrations(version text primary key, appliquee_le timestamptz not null default now())` — créée par `appliquer_migrations` si absente.
- `titre(id bigint generated always as identity primary key, symbole text not null, place text not null, nom text not null, devise text not null, actif boolean not null default true, panel_temoin boolean not null default false, est_reference boolean not null default false, unique (symbole, place))`.
- `cours_journalier(titre_id bigint not null references titre(id), jour date not null, ouverture numeric(18,6) not null, haut numeric(18,6) not null, bas numeric(18,6) not null, cloture numeric(18,6) not null, volume bigint not null, source text not null, recupere_le timestamptz not null, primary key (titre_id, jour))`.
- Un déclencheur qui lève une exception sur tout `UPDATE` ou `DELETE` de `cours_journalier` (ajout seul garanti par la base, en plus du code).
- `execution(id bigint generated always as identity primary key, date_marche date not null unique, declencheur text not null check (declencheur in ('cron','manuel','rattrapage')), statut text not null check (statut in ('en_cours','ok','partielle','sans_objet','echec')), debut timestamptz not null, fin timestamptz, nb_cours_enregistres integer not null default 0, erreurs jsonb not null default '[]', titres_en_retard jsonb not null default '[]', credits_consommes integer not null default 0)`.

- [x] **Étape 1 : écrire les tests qui échouent**

```python
import pytest
from bourse_jev.adaptateurs.postgres import appliquer_migrations, connecter

def test_migrations_idempotentes(conn_test, dossier_migrations):
    assert appliquer_migrations(conn_test, dossier_migrations) == ["001_socle"]
    assert appliquer_migrations(conn_test, dossier_migrations) == []

def test_modification_d_un_cours_refusee_par_la_base(depot_postgres_avec_un_cours, conn_test):
    with pytest.raises(Exception):
        conn_test.execute("UPDATE cours_journalier SET cloture = 1")

def test_connecter_reessaie_une_fois_apres_5_secondes():
    appels, attentes = [], []
    def ouvrir(dsn):
        appels.append(dsn)
        if len(appels) == 1:
            raise OSError("base en veille")
        return "connexion"
    assert connecter("dsn", attendre=attentes.append, ouvrir=ouvrir) == "connexion"
    assert attentes == [5.0]

def test_connecter_echoue_apres_deux_tentatives():
    def ouvrir(dsn):
        raise OSError("injoignable")
    with pytest.raises(OSError):
        connecter("dsn", attendre=lambda s: None, ouvrir=ouvrir)
```

Fixtures (`tests/conftest.py`) : `conn_test` ouvre `TEST_DATABASE_URL`, recrée un schéma vide pour chaque test (`DROP SCHEMA public CASCADE; CREATE SCHEMA public`) et saute le test (`pytest.skip`) si la variable est absente ; `dossier_migrations` pointe vers `migrations/` ; `depot_postgres_avec_un_cours` applique les migrations, enregistre le titre AAPL puis `fabriquer_cours(titre_id=<son id>)`.

- [x] **Étape 2 : vérifier l'échec** — `TEST_DATABASE_URL=… uv run pytest tests/adaptateurs/test_postgres.py -v` (Postgres local : `docker run -e POSTGRES_PASSWORD=test -e POSTGRES_USER=test -e POSTGRES_DB=test -p 5432:5432 postgres:16`).
- [x] **Étape 3 : écrire `001_socle.sql`, `connecter`, `appliquer_migrations` et `DepotPostgres`** — chaque migration dans sa propre transaction ; `enregistrer_cours` en `INSERT … ON CONFLICT (titre_id, jour) DO NOTHING` et renvoie `rowcount == 1` ; `debuter_execution` en `INSERT … ON CONFLICT (date_marche) DO UPDATE SET statut = 'en_cours', declencheur = …, debut = … RETURNING id`.
- [x] **Étape 4 : brancher la suite de contrat** — ajouter `"postgres"` aux paramètres de la fixture `depot` (migrations appliquées sur la base de test).
- [x] **Étape 5 : vérifier** — `uv run pytest tests/contrat tests/adaptateurs/test_postgres.py -v` : la suite de contrat passe pour `memoire` et `postgres`.
- [x] **Étape 6 : commit** — `feat(adaptateurs): schéma Postgres, migrations et dépôt Postgres`

---

### Tâche 7 : source de cours Twelve Data

**Fichiers :**
- Créer : `src/bourse_jev/adaptateurs/twelve_data.py`, `tests/fixtures/twelve_data/time_series_aapl.json`, `tests/fixtures/twelve_data/erreur_429.json`, `tests/fixtures/twelve_data/erreur_symbole.json`, `tests/fixtures/twelve_data/malformee.json`
- Test : `tests/adaptateurs/test_twelve_data.py`

**Interfaces :**
- Consomme : le port `SourceDeCours`, `CoursBrut`, `QuotaAtteint`, `SourceIndisponible`.
- Produit : `SourceTwelveData(cle_api: str, client: httpx.Client | None = None, credits_par_minute: int = 8, credits_par_jour: int = 800, attendre: Callable[[float], None] = time.sleep, horloge_s: Callable[[], float] = time.monotonic)` ; `nom = "twelve_data"` ; `credits_consommes: int`.

Appel : `GET https://api.twelvedata.com/time_series` avec `symbol`, `interval=1day`, `outputsize=5`, `adjust=none`, `apikey`. Réponse attendue : `{"meta": {...}, "values": [{"datetime": "2026-10-27", "open": "…", "high": "…", "low": "…", "close": "…", "volume": "…"}], "status": "ok"}`, valeurs numériques en chaînes. Erreur : `{"code": 429, "message": "…", "status": "error"}`.

Contenu de `time_series_aapl.json` (valeurs fictives) : trois barres, `2026-10-27` (open `231.10`, high `233.80`, low `230.40`, close `232.95`, volume `48210500`), `2026-10-24`, `2026-10-23`.

- [x] **Étape 1 : écrire les tests qui échouent**

```python
import json
from datetime import date
from decimal import Decimal as D
from pathlib import Path
import httpx
import pytest
from bourse_jev.adaptateurs.twelve_data import SourceTwelveData
from bourse_jev.domaine.erreurs import QuotaAtteint, SourceIndisponible

FIX = Path(__file__).parents[1] / "fixtures" / "twelve_data"

def source_avec(nom_fixture, statut_http=200, attentes=None, requetes=None):
    corps = json.loads((FIX / nom_fixture).read_text())
    def repondre(requete):
        if requetes is not None:
            requetes.append(requete)
        return httpx.Response(statut_http, json=corps)
    client = httpx.Client(transport=httpx.MockTransport(repondre))
    return SourceTwelveData("cle", client=client, attendre=(attentes or []).append, horloge_s=lambda: 0.0)

def test_cours_du_jour_present():
    cours = source_avec("time_series_aapl.json").cours_du_jour("AAPL", date(2026, 10, 27))
    assert cours.cloture == D("232.95") and cours.volume == 48210500 and cours.jour == date(2026, 10, 27)

def test_jour_absent_renvoie_none_sans_prendre_la_veille():
    assert source_avec("time_series_aapl.json").cours_du_jour("AAPL", date(2026, 10, 28)) is None

def test_parametres_envoyes():
    requetes = []
    source_avec("time_series_aapl.json", requetes=requetes).cours_du_jour("AAPL", date(2026, 10, 27))
    params = requetes[0].url.params
    assert params["symbol"] == "AAPL" and params["interval"] == "1day" and params["adjust"] == "none"

def test_erreur_429_leve_quota_atteint():
    with pytest.raises(QuotaAtteint):
        source_avec("erreur_429.json").cours_du_jour("AAPL", date(2026, 10, 27))

def test_reponse_erreur_metier_leve_source_indisponible():
    with pytest.raises(SourceIndisponible, match="ZZZZ"):
        source_avec("erreur_symbole.json").cours_du_jour("ZZZZ", date(2026, 10, 27))

def test_reponse_malformee_leve_source_indisponible():
    with pytest.raises(SourceIndisponible):
        source_avec("malformee.json").cours_du_jour("AAPL", date(2026, 10, 27))

def test_quota_journalier_interne_respecte():
    source = source_avec("time_series_aapl.json")
    source.credits_par_jour = 2
    source.cours_du_jour("AAPL", date(2026, 10, 27))
    source.cours_du_jour("AAPL", date(2026, 10, 27))
    with pytest.raises(QuotaAtteint):
        source.cours_du_jour("AAPL", date(2026, 10, 27))
    assert source.credits_consommes == 2

def test_neuvieme_appel_de_la_minute_attend():
    attentes = []
    source = source_avec("time_series_aapl.json", attentes=attentes)
    for _ in range(9):
        source.cours_du_jour("AAPL", date(2026, 10, 27))
    assert len(attentes) == 1 and attentes[0] > 0

@pytest.mark.reel
def test_contrat_reel_twelve_data():
    """Appel réel, exclu par défaut : `uv run pytest -m reel` avec TWELVE_DATA_API_KEY défini."""
```

`malformee.json` : `status: ok` et une barre du 27/10/2026 sans champ `close`. `erreur_symbole.json` : `{"code": 404, "message": "symbol ZZZZ not found", "status": "error"}`.

- [x] **Étape 2 : vérifier l'échec** — `uv run pytest tests/adaptateurs/test_twelve_data.py -v`
- [x] **Étape 3 : implémenter `SourceTwelveData.cours_du_jour`**

Limitation par fenêtre glissante : une `deque` des instants d'appel ; retirer ceux de plus de 60 s ; s'il en reste 8, attendre `60 - (maintenant - plus_ancien)` secondes puis retirer le plus ancien (ne pas relire l'horloge en boucle : le test utilise une horloge figée). Contrôler le quota journalier interne **avant** l'appel. Code 429 (HTTP ou dans le corps) → `QuotaAtteint` ; tout autre `status: error`, erreur réseau ou champ manquant/non numérique → `SourceIndisponible` dont le message contient le symbole. Conversion des chaînes en `Decimal` et du volume en `int`.

- [x] **Étape 4 : vérifier** — les tests passent (le test `reel` est exclu).
- [x] **Étape 5 : écrire le corps du test `reel`** (un appel AAPL sur le dernier jour de bourse ; vérifie un `CoursBrut` cohérent) et le lancer une fois à la main : `uv run pytest -m reel -v`. Si le format réel diffère des fixtures, corriger les fixtures, pas le test réel.
  > Exécution : test réel passé le 28/10/2026 (clé en en-tête acceptée, format conforme aux fixtures). Un premier essai avec une clé mal collée (34 caractères non alphanumériques) a renvoyé un HTTP 400 au corps non JSON : le message « réponse illisible » inclut désormais un extrait du corps, sans la clé.
  > Écart (exécution) : `outputsize=30` au lieu de 5 (5 barres ne couvrent pas une fenêtre de rattrapage de 10 jours de bourse ; même coût en crédits) ; clé envoyée en en-tête `Authorization: apikey …` et non en paramètre `apikey`, pour qu'elle n'apparaisse jamais dans une URL journalisée.
- [x] **Étape 6 : commit** — `feat(adaptateurs): source de cours Twelve Data avec limitation de débit`

---

### Tâche 8 : catalogue et panel témoin

**Fichiers :**
- Créer : `config/panel_temoin.csv`, `src/bourse_jev/application/catalogue.py`
- Test : `tests/application/test_catalogue.py`

**Interfaces :**
- Consomme : `Titre`, le port `Depot`.
- Produit : `charger_panel(chemin: Path) -> list[Titre]` ; `synchroniser_catalogue(depot: Depot, titres: list[Titre]) -> int` (nombre de titres ajoutés).

`panel_temoin.csv` — colonnes `symbole,nom,place,devise,role` (`role` = `panel` ou `reference`). Trente titres répartis entre secteurs, pour ne pas reproduire le biais « technologie à la mode » : AAPL, MSFT, NVDA, AMZN, GOOGL, META (technologie et communication), JPM, BAC, V, MA (finance), JNJ, PFE, UNH, LLY (santé), XOM, CVX (énergie), PG, KO, PEP, WMT, COST (consommation de base), HD, MCD, DIS (consommation cyclique), CAT, BA, GE (industrie), NEE (services aux collectivités), T, VZ (télécoms) ; plus SPY en `reference`. Place `XNYS` pour tous (simplification v1 : la place sert d'identifiant interne, pas d'adresse de cotation), devise `USD`.

- [x] **Étape 1 : écrire les tests qui échouent**

```python
from pathlib import Path
from bourse_jev.adaptateurs.memoire_depot import DepotEnMemoire
from bourse_jev.application.catalogue import charger_panel, synchroniser_catalogue

PANEL = Path(__file__).parents[2] / "config" / "panel_temoin.csv"

def test_panel_de_30_titres_et_une_reference():
    titres = charger_panel(PANEL)
    assert sum(t.panel_temoin for t in titres) == 30
    assert [t.symbole for t in titres if t.est_reference] == ["SPY"]

def test_synchronisation_idempotente():
    depot, titres = DepotEnMemoire(), charger_panel(PANEL)
    assert synchroniser_catalogue(depot, titres) == 31
    assert synchroniser_catalogue(depot, titres) == 0
```

- [x] **Étape 2 : vérifier l'échec** — `uv run pytest tests/application/test_catalogue.py -v`
- [x] **Étape 3 : écrire le CSV et implémenter les deux fonctions** (module `csv` de la bibliothèque standard).
- [x] **Étape 4 : vérifier** — les tests passent.
- [x] **Étape 5 : commit** — `feat(catalogue): panel témoin de 30 titres et ETF de référence`

---

### Tâche 9 : cas d'usage `collecter` (idempotence, rattrapage, erreurs)

**Fichiers :**
- Créer : `src/bourse_jev/application/collecte.py`
- Modifier : `tests/doublures.py` (ajout de `SourceFactice` et `CalendrierFactice`), `src/bourse_jev/adaptateurs/memoire_depot.py` (lectures réservées aux tests)
- Test : `tests/application/test_collecte.py`, fixtures dans `tests/application/conftest.py`

**Interfaces :**
- Consomme : tous les ports (tâche 3), `valider_cours`, `DepotEnMemoire` (tests).
- Produit : `collecter(aujourd_hui: date, declencheur: Declencheur, depot: Depot, source: SourceDeCours, calendrier: CalendrierDeMarche, horloge: Horloge, fenetre_rattrapage: int = 10) -> list[RapportExecution]`.
- Doublures : `SourceFactice(reponses: dict[tuple[str, date], CoursBrut | Exception])` (absent du dictionnaire = `None`) ; `CalendrierFactice(jours: list[date])`.

Algorithme :

```text
jours = calendrier.jours_de_bourse(aujourd_hui - 30 jours, aujourd_hui)[-fenetre_rattrapage:]
a_traiter = [] si jours est vide, sinon [j for j in jours if j not in depot.dates_reussies(depuis=jours[0])]   (croissant)
si a_traiter est vide :
    si aujourd_hui n'est pas un jour de bourse : enregistrer et renvoyer une exécution SANS_OBJET datée d'aujourd'hui
    sinon : renvoyer []                                   (tout est déjà fait)
pour chaque jour de a_traiter :
    declencheur du jour = declencheur si jour == aujourd_hui, sinon RATTRAPAGE
    pour chaque titre de depot.titres_a_collecter() :
        brut = source.cours_du_jour(titre.symbole, jour)
            QuotaAtteint → ce titre et les suivants vont dans titres_en_retard ; arrêter APRÈS ce jour (les jours suivants seront rattrapés)
            SourceIndisponible ou autre exception → erreur "<SYMBOLE> : <message>", titre suivant
        None → erreur "<SYMBOLE> : cours absent pour <jour>"
        motif = valider_cours(cours, depot.cloture_precedente(titre.id, avant=jour)) → si motif : erreur "<SYMBOLE> : rejeté (<motif>)"
        sinon depot.enregistrer_cours(cours) ; un cours déjà présent compte comme réussi
    statut = OK si aucune erreur ni retard ; ECHEC si aucun cours réussi ; PARTIELLE sinon
```

`credits_consommes` du rapport = différence de `source.credits_consommes` sur le jour.

- [x] **Étape 1 : écrire les tests qui échouent**

```python
from datetime import date
from bourse_jev.application.collecte import collecter
from bourse_jev.domaine.erreurs import QuotaAtteint, SourceIndisponible
from bourse_jev.domaine.modeles import Declencheur, StatutExecution as S
from tests.doublures import CalendrierFactice, SourceFactice
from tests.application.aides import cours_de, cours_stocke, declencheur_enregistre, id_de, marquer_reussi

L26, M27, ME28 = date(2026, 10, 26), date(2026, 10, 27), date(2026, 10, 28)
SAMEDI = date(2026, 10, 31)

# fixtures (conftest) : depot_3_titres (AAPL, MSFT, SPY), calendrier ([L26, M27, ME28]),
# horloge (28/10/2026 21:45 UTC), brut(jour, cloture="100") -> CoursBrut

def test_collecte_nominale(depot_3_titres, calendrier, horloge, source_complete):
    rapports = collecter(ME28, Declencheur.CRON, depot_3_titres, source_complete(ME28), calendrier, horloge, fenetre_rattrapage=1)
    assert [(r.date_marche, r.statut, r.nb_cours_enregistres) for r in rapports] == [(ME28, S.OK, 3)]

def test_deuxieme_execution_ne_fait_rien(depot_3_titres, calendrier, horloge, source_complete):
    src = source_complete(ME28)
    collecter(ME28, Declencheur.CRON, depot_3_titres, src, calendrier, horloge, fenetre_rattrapage=1)
    assert collecter(ME28, Declencheur.MANUEL, depot_3_titres, src, calendrier, horloge, fenetre_rattrapage=1) == []

def test_jour_manque_rattrape_dans_l_ordre(depot_3_titres, calendrier, horloge, source_complete):
    marquer_reussi(depot_3_titres, L26)
    rapports = collecter(ME28, Declencheur.CRON, depot_3_titres, source_complete(M27, ME28), calendrier, horloge)
    assert [r.date_marche for r in rapports] == [M27, ME28]
    assert [declencheur_enregistre(depot_3_titres, d) for d in (M27, ME28)] == [Declencheur.RATTRAPAGE, Declencheur.CRON]

def test_rattrapage_limite_a_la_fenetre(depot_3_titres, calendrier, horloge, source_complete):
    rapports = collecter(ME28, Declencheur.CRON, depot_3_titres, source_complete(M27, ME28), calendrier, horloge, fenetre_rattrapage=2)
    assert [r.date_marche for r in rapports] == [M27, ME28]

def test_jour_non_ouvre_marque_sans_objet(depot_3_titres, horloge):
    rapports = collecter(SAMEDI, Declencheur.CRON, depot_3_titres, SourceFactice({}), CalendrierFactice([]), horloge)
    assert [(r.date_marche, r.statut) for r in rapports] == [(SAMEDI, S.SANS_OBJET)]

def test_erreur_sur_un_titre_n_arrete_pas_les_autres(depot_3_titres, calendrier, horloge, brut):
    src = SourceFactice({("AAPL", ME28): brut(ME28), ("MSFT", ME28): SourceIndisponible("MSFT : 404"), ("SPY", ME28): brut(ME28)})
    [r] = collecter(ME28, Declencheur.CRON, depot_3_titres, src, calendrier, horloge, fenetre_rattrapage=1)
    assert r.statut is S.PARTIELLE and r.nb_cours_enregistres == 2
    assert any("MSFT" in e for e in r.erreurs)

def test_cours_absent_n_est_pas_remplace_par_la_veille(depot_3_titres, calendrier, horloge, brut):
    src = SourceFactice({("AAPL", M27): brut(M27)})
    [r] = collecter(ME28, Declencheur.CRON, depot_3_titres, src, calendrier, horloge, fenetre_rattrapage=1)
    assert r.statut is S.ECHEC and r.nb_cours_enregistres == 0
    assert any("cours absent" in e for e in r.erreurs)

def test_cours_aberrant_rejete(depot_3_titres, calendrier, horloge, brut):
    tid = id_de(depot_3_titres, "AAPL")
    depot_3_titres.enregistrer_cours(cours_stocke(tid, M27, cloture="100"))
    src = SourceFactice({("AAPL", ME28): brut(ME28, cloture="200"), ("MSFT", ME28): brut(ME28), ("SPY", ME28): brut(ME28)})
    [r] = collecter(ME28, Declencheur.CRON, depot_3_titres, src, calendrier, horloge, fenetre_rattrapage=1)
    assert any("AAPL" in e and "variation_aberrante" in e for e in r.erreurs)

def test_quota_atteint_reporte_les_titres_restants(depot_3_titres, calendrier, horloge, brut):
    src = SourceFactice({("AAPL", ME28): brut(ME28), ("MSFT", ME28): QuotaAtteint("800/jour")})
    [r] = collecter(ME28, Declencheur.CRON, depot_3_titres, src, calendrier, horloge, fenetre_rattrapage=1)
    assert r.statut is S.PARTIELLE and r.titres_en_retard == ["MSFT", "SPY"]

def test_recupere_le_vient_de_l_horloge(depot_3_titres, calendrier, horloge, source_complete):
    collecter(ME28, Declencheur.CRON, depot_3_titres, source_complete(ME28), calendrier, horloge, fenetre_rattrapage=1)
    assert cours_de(depot_3_titres, "AAPL", ME28).recupere_le == horloge.maintenant()
```

Les fonctions d'aide `marquer_reussi(depot, jour)`, `declencheur_enregistre(depot, jour)`, `id_de(depot, symbole)`, `cours_stocke(titre_id, jour, cloture)` et `cours_de(depot, symbole, jour)` vivent dans `tests/application/aides.py` (avec `tests/application/__init__.py`) ; les fixtures `depot_3_titres`, `calendrier`, `horloge`, `brut` et `source_complete` (fabrique : `source_complete(*jours)` renvoie une `SourceFactice` qui répond un cours normal pour les 3 titres à chacun de ces jours) vivent dans `tests/application/conftest.py`. `brut(jour, cloture="100")` renvoie un `CoursBrut` dont ouverture, haut, bas et clôture valent tous `cloture` et le volume 1000. `declencheur_enregistre` et `cours_de` lisent l'état par deux méthodes de lecture réservées aux tests, ajoutées à `DepotEnMemoire` dans cette tâche : `execution_du(jour) -> tuple[Declencheur, StatutExecution]` et `cours_du(titre_id, jour) -> CoursJournalier | None`.

- [x] **Étape 2 : vérifier l'échec** — `uv run pytest tests/application/test_collecte.py -v`
- [x] **Étape 3 : implémenter `collecter`** selon l'algorithme ci-dessus.
- [x] **Étape 4 : vérifier** — tous les tests du projet passent : `uv run pytest -v`.
- [x] **Étape 5 : commit** — `feat(collecte): collecte quotidienne idempotente avec rattrapage`

---

### Tâche 10 : ligne de commande, batch planifié et mise en service

**Fichiers :**
- Créer : `src/bourse_jev/__main__.py`, `.github/workflows/collecte.yml`
- Test : `tests/test_cli.py`

**Interfaces :**
- Consomme : `charger_configuration`, `connecter`, `appliquer_migrations`, `DepotPostgres`, `charger_panel`, `synchroniser_catalogue`, `SourceTwelveData`, `CalendrierXNYS`, `HorlogeSysteme`, `jour_de_marche_courant`, `collecter`.
- Produit : `main(argv: list[str] | None = None) -> int` ; sous-commandes `migrer`, `catalogue`, `collecter [--date AAAA-MM-JJ] [--declencheur cron|manuel]` ; code de sortie `0` si tous les rapports sont `OK`, `SANS_OBJET` ou `PARTIELLE` (ou s'il n'y a rien à faire), `1` si au moins un rapport est `ECHEC`, `2` pour une configuration incomplète.

- [x] **Étape 1 : écrire les tests qui échouent**

```python
from bourse_jev.__main__ import code_de_sortie, lire_arguments
from bourse_jev.domaine.modeles import StatutExecution as S

def test_arguments_collecter():
    args = lire_arguments(["collecter", "--date", "2026-10-28", "--declencheur", "manuel"])
    assert args.commande == "collecter" and str(args.date) == "2026-10-28" and args.declencheur == "manuel"

def test_date_par_defaut_absente():
    assert lire_arguments(["collecter"]).date is None

def test_code_de_sortie():
    assert code_de_sortie([]) == 0
    assert code_de_sortie([S.OK, S.PARTIELLE, S.SANS_OBJET]) == 0
    assert code_de_sortie([S.OK, S.ECHEC]) == 1
```

- [x] **Étape 2 : vérifier l'échec** — `uv run pytest tests/test_cli.py -v`
- [x] **Étape 3 : implémenter `main`, `lire_arguments` et `code_de_sortie`** — sans `--date`, la date vient de `jour_de_marche_courant(HorlogeSysteme().maintenant())`. Afficher un résumé par rapport (date, statut, nombre de cours, erreurs) et, pour `PARTIELLE`, une ligne `::warning::` lisible dans GitHub Actions.
- [x] **Étape 4 : écrire `.github/workflows/collecte.yml`** — déclencheurs : `schedule` avec `cron: "45 21 * * 1-5"` (21 h 45 UTC, après la clôture de New York en heure d'été comme d'hiver) et `workflow_dispatch` ; secrets `DATABASE_URL` et `TWELVE_DATA_API_KEY` ; étapes : `uv sync`, `uv run python -m bourse_jev migrer`, `… catalogue`, `… collecter` ; `timeout-minutes: 30` (31 titres à 8 par minute ≈ 4 minutes, plus le rattrapage).
- [x] **Étape 5 : vérifier localement** — `uv run pytest -v`, `uv run ruff check .` et `uv run mypy src` passent.
- [x] **Étape 6 : commit** — `feat(cli): commandes migrer, catalogue, collecter et batch planifié`
  > Écart (exécution) : le workflow passe `--declencheur cron` sur `schedule` et `manuel` sur `workflow_dispatch` ; groupe `concurrency` pour empêcher deux collectes simultanées ; dépendances de dev non installées en production (`--no-dev`). Les messages d'API sont mis sur une seule ligne avant affichage, pour qu'ils ne puissent pas forger une commande de workflow `::…::`.
- [ ] **Étape 7 : mise en service (manuelle, par Valentin)**
  1. Créer le projet Neon et récupérer la chaîne de connexion.
  2. Créer la clé Twelve Data (offre Basic).
  3. Déclarer les secrets `DATABASE_URL` et `TWELVE_DATA_API_KEY` dans GitHub (Settings → Secrets and variables → Actions).
  4. Lancer le workflow `collecte` à la main une fois : attendu, une exécution `OK` (ou `PARTIELLE` expliquée) et 31 lignes dans `cours_journalier` pour le dernier jour de bourse.
- [ ] **Étape 8 : critère de sortie du lot** — après 5 jours de bourse consécutifs, la table `execution` contient 5 lignes `ok` déclenchées par `cron`, sans intervention. Mettre à jour `docs/plans/00-feuille-de-route.md`.
