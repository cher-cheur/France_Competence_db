# France Compétences DB

Construit une base SQLite à partir de l'**export open data quotidien** des répertoires
RNCP et RS publié par France Compétences sur
[data.gouv.fr](https://www.data.gouv.fr/fr/datasets/repertoire-national-des-certifications-professionnelles/)
(Licence Ouverte / Etalab 2.0).

Toutes les fiches sont couvertes (actives et inactives), avec leurs certificateurs,
organismes partenaires, blocs de compétences, codes ROME / NSF / Formacode,
conventions collectives, voies d'accès et filiations.

## Utilisation

Python 3.10 ou plus récent.

```bash
pip install -r requirements.txt
```

```bash
python run_pipeline.py
```

Le pipeline télécharge l'export CSV le plus récent dans `data/`, puis reconstruit
`data/rncp.sqlite`. La base est générée dans un fichier temporaire et ne remplace
l'ancienne qu'en cas de succès. Le téléchargement est relancé automatiquement en cas
de coupure réseau.

Options :

| Option | Rôle |
|---|---|
| `--date AAAA-MM-JJ` | charger l'export d'une date précise |
| `--zip chemin.zip` | utiliser une archive déjà téléchargée |
| `--data-dir`, `--db` | changer les emplacements par défaut |

Les étapes peuvent aussi être lancées séparément :

```bash
python download.py
```

```bash
python load.py data/export-fiches-csv-AAAA-MM-JJ.zip --db data/rncp.sqlite
```

## Modèle de données

Toutes les tables sont reliées par `numero_fiche` (`RNCP35288`, `RS5487`…). Un même
numéro peut exister à la fois en RNCP et en RS : l'identifiant complet est donc la clé.

| Table | Contenu |
|---|---|
| `fiches` | intitulé, type, niveau (3 à 8), dates, actif, `apprentissage` (déduit des voies d'accès) |
| `organismes` | SIRET (texte, 14 chiffres) et nom |
| `certificateurs` | fiche ↔ organisme certificateur |
| `partenaires` | fiche ↔ organisme habilité, avec `habilitation`, `peut_former`, `peut_evaluer` |
| `partenaires_sans_siret` | partenaires déclarés sans SIRET |
| `blocs_competences` | code et libellé des blocs |
| `rome`, `nsf`, `formacode`, `ccn` | nomenclatures |
| `fiches_rome`, `fiches_nsf`, `fiches_formacode`, `fiches_ccn` | liaisons |
| `voies_acces` | formation continue, VAE, apprentissage… |
| `filiations` | ancienne certification → nouvelle |
| `chargements` | date de l'export chargé |

Habilitations des partenaires :

| Code | Former | Organiser l'évaluation |
|---|---|---|
| `HABILITATION_ORGA_FORM` | oui | oui |
| `HABILITATION_FORMER` | oui | non |
| `HABILITATION_ORGANISER` | non | oui |

## Exemples de requêtes

Certifications actives en IA ou data, avec le nombre d'organismes partenaires :

```sql
SELECT f.numero_fiche, f.intitule, f.niveau, f.date_fin_enregistrement,
       COUNT(p.siret) AS nb_partenaires
FROM fiches f
LEFT JOIN partenaires p USING (numero_fiche)
WHERE f.actif
  AND (f.intitule LIKE '%intelligence artificielle%' OR f.intitule LIKE '%data%')
GROUP BY f.numero_fiche
ORDER BY nb_partenaires DESC;
```

Certifications actives qui arrivent à échéance dans les 6 mois :

```sql
SELECT numero_fiche, intitule, date_fin_enregistrement
FROM fiches
WHERE actif AND date_fin_enregistrement <= date('now', '+6 months')
ORDER BY date_fin_enregistrement;
```

Certifications actives liées au code ROME M1805 (études et développement informatique) :

```sql
SELECT f.numero_fiche, f.intitule
FROM fiches_rome fr JOIN fiches f USING (numero_fiche)
WHERE fr.code_rome = 'M1805' AND f.actif;
```

## Tests

```bash
python -m pytest
```

## Licence

MIT
