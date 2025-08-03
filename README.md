# RNCP Database Automation

Ce projet automatise l'extraction, le nettoyage, le scraping et l'import des données France Compétences (RNCP/RS) dans une base de données SQLite structurée.

## Processus automatisé

1. **Extraction depuis Excel**  
   `process_excel.py` extrait et structure les données principales et relationnelles depuis un fichier Excel source.

2. **Scraping des organismes partenaires**  
   `scrape_organismes.py` télécharge et structure les partenaires (formateurs, évaluateurs, certificateurs) pour chaque code RNCP/RS.

3. **Création de la base de données**  
   `create_database.py` crée la base SQLite et les tables selon le modèle relationnel.

4. **Peuplement de la base**  
   `populate_database.py` importe tous les fichiers CSV dans la base.

5. **Automatisation complète**  
   `run_full_process.py` exécute toutes les étapes ci-dessus dans l'ordre, en utilisant le dossier `csv4db` pour stocker les CSV intermédiaires.

## Structure des dossiers

- `csv4db/` : Dossier contenant tous les fichiers CSV générés pour l'import en base.

## Utilisation

```bash
python run_full_process.py
```

## Dépendances

Voir `requirements.txt`.

## Licence

MIT

## Déploiement sur GitHub

1. Crée un nouveau repository sur GitHub (via l'interface web).
2. Ajoute le remote à ton projet local :
   ```bash
   git remote add origin https://github.com/<ton-utilisateur>/<nom-du-repo>.git
   ```
3. Pousse ton commit sur la branche principale :
   ```bash
   git push -u origin main
   ```
   (ou `master` selon le nom de ta branche)

4. Vérifie sur GitHub que tes fichiers sont bien présents.
