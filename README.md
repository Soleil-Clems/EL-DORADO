# El Dorado — Pipeline ETL

Un petit pipeline ETL (Extract, Transform, Load) qui récupère des métadonnées de
livres depuis une API publique (Gutendex, Project Gutenberg) et un fichier CSV
local de reviews mal formaté, nettoie et croise ces deux sources, puis charge le
résultat dans une base de données SQLite.

Construit autour de l'**architecture médaillon** : bronze (données brutes) →
silver (nettoyées, jointes) → gold (SQLite, prêtes à interroger).

```
 Mine A : API Gutendex --+
                          +--> EXTRACT -> data/bronze/ (brut, non modifié)
 Mine B : CSV sale ------+
                          TRANSFORM -> data/silver/ (nettoyé, typé, joint, dédupliqué)
                          LOAD -> data/refinery.db (SQLite = le coffre-fort d'or)
```

## Ce que fait le projet

- **Extract** : récupère les livres en anglais depuis Gutendex (avec pagination)
  et copie le CSV de reviews brut — les deux sont sauvegardés tels quels dans
  `data/bronze/`.
- **Transform** : nettoie le CSV (corrige les dates, les espaces superflus, la
  casse, les notes hors bornes, les doublons, les valeurs manquantes), réduit les
  données de l'API aux champs nécessaires, joint les deux sources sur `book_id`
  (en gardant les livres de l'API sans review), et écrit le résultat dans
  `data/silver/clean.json`.
- **Load** : insère les données nettoyées dans une base SQLite, en utilisant
  `INSERT OR REPLACE` pour que le pipeline soit idempotent — le relancer
  plusieurs fois ne crée jamais de doublons.
- **Stats** : rapporte le nombre de lignes par couche et les lignes rejetées avec
  leurs raisons.

## Prérequis

- Python 3.12+
- Dépendances : `requests`, `pyyaml`, `pandas`, `python-dateutil`

## Installation

```bash
pip install -r requirements.txt
# ou, avec uv
uv sync
```

## Utilisation

```bash
python refinery.py extract     # récupère les deux sources dans data/bronze/
python refinery.py transform   # nettoie + joint dans data/silver/clean.json
python refinery.py load        # insère dans data/refinery.db (SQLite)
python refinery.py run         # extract -> transform -> load, en une commande
python refinery.py stats       # rapporte les comptages par couche + les rejets
```

## Configuration

Tous les chemins des sources et les paramètres de l'API vivent dans
`config.yaml` — rien n'est codé en dur dans le script.

## Choix de conception

- **Bronze reste intact** pour pouvoir corriger et relancer la logique de
  transformation sans avoir à re-solliciter le réseau.
- **L'idempotence** est garantie au niveau du chargement grâce à
  `INSERT OR REPLACE` sur `book_id` (la clé primaire).
- **`subjects`** (une liste) est stockée comme une chaîne JSON dans SQLite,
  puisque SQLite n'a pas de type tableau natif.
- **Les dates** sont stockées en `TEXT` au format `YYYY-MM-DD` (ISO 8601), la
  convention recommandée par SQLite en l'absence de type date natif.