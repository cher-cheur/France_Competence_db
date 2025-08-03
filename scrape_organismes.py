import os
import pandas as pd
import requests
from bs4 import BeautifulSoup
from read_excel import read_excel_from_url  # Importer la fonction pour lire les fichiers Excel
import time
import random

def scrape_organismes(repertoires_csv: str, output_dir: str, organismes_csv: str):
    """
    Scrape les pages pour chaque code et type dans les 10 premières lignes de Repertoires.csv,
    lit les fichiers Excel associés, traite les rôles, et enregistre les résultats dans des fichiers CSV.

    Args:
        repertoires_csv (str): Chemin vers le fichier Repertoires.csv.
        output_dir (str): Répertoire où enregistrer les fichiers CSV.
        organismes_csv (str): Chemin vers le fichier Organismes.csv pour vérifier et ajouter les SIRET manquants.
    """
    # Charger le fichier Repertoires.csv
    df_repertoires = pd.read_csv(repertoires_csv)

    # Limiter le traitement aux 10 premières lignes
    df_repertoires = df_repertoires.head(10)

    # Charger ou initialiser le fichier Organismes.csv
    if os.path.exists(organismes_csv):
        df_organismes = pd.read_csv(organismes_csv, dtype={"siret": str})
    else:
        df_organismes = pd.DataFrame(columns=["siret", "nom"])

    # Convertir la colonne 'siret' en entier dans Organismes.csv si elle existe
    if not df_organismes.empty:
        df_organismes["siret"] = pd.to_numeric(df_organismes["siret"], errors="coerce").dropna().astype(int)

    # Créer le répertoire de sortie s'il n'existe pas
    os.makedirs(output_dir, exist_ok=True)

    # Initialiser les DataFrames pour les évaluateurs, formateurs et ceux sans SIRET
    evaluateurs = []  # Liste pour les évaluateurs avec SIRET
    formateurs = []  # Liste pour les formateurs avec SIRET
    evaluateurs_sans_siret = []  # Liste pour les évaluateurs sans SIRET
    formateurs_sans_siret = []  # Liste pour les formateurs sans SIRET
    organismes_sans_siret = []  # Liste pour les organismes sans SIRET
    certificateurs_sans_siret = []  # Liste pour les certificateurs sans SIRET

    # Démarrer le chronomètre
    start_time = time.time()

    # Parcourir chaque ligne du fichier
    for _, row in df_repertoires.iterrows():
        code = str(row["code"]).strip()
        type_ = str(row["type"]).strip().lower()  # Convertir en minuscule pour l'URL
        url = f"https://www.francecompetences.fr/recherche/{type_}/{code}"

        try:
            # Récupérer la page HTML
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            # Chercher la balise <a> avec le title "Listes des organismes préparant la certification"
            link = soup.find("a", title=" Liste des organismes préparant à la certification")
            if link:
                href = link.get("href")
                if href:
                    # Construire l'URL complète
                    excel_url = f"https://www.francecompetences.fr{href}"

                    # Lire le fichier Excel
                    df_excel = read_excel_from_url(excel_url)

                    # Vérifier si les colonnes nécessaires existent
                    if all(col in df_excel.columns for col in ["Nom de l'organisme", "SIRET", "Rôle du partenaire"]):
                        # Extraire les colonnes nécessaires
                        df_result = df_excel[["Nom de l'organisme", "SIRET", "Rôle du partenaire"]].rename(
                            columns={
                                "Nom de l'organisme": "ecole",
                                "SIRET": "siret",
                                "Rôle du partenaire": "role"
                            }
                        )
                        # Ajouter la colonne code_rep
                        df_result["code_rep"] = code

                        # Appliquer la logique pour les rôles
                        df_result['formateur'] = df_result['role'].str.contains("former", case=False, na=False)
                        df_result['evaluateur'] = df_result['role'].str.contains("évaluation", case=False, na=False)

                        # Ajouter les formateurs et évaluateurs aux DataFrames correspondants
                        for _, row_result in df_result.iterrows():
                            siret = row_result["siret"]
                            nom = row_result["ecole"]

                            # Vérifier si le SIRET est valide
                            if pd.notna(siret) and str(siret).isdigit():
                                siret = int(siret)  # Convertir le SIRET en entier

                                # Ajouter à Evaluateurs
                                if row_result["evaluateur"]:
                                    evaluateurs.append({"code_rep": code, "siret": siret})

                                # Ajouter à Formateurs
                                if row_result["formateur"]:
                                    formateurs.append({"code_rep": code, "siret": siret})

                                # Vérifier et ajouter dans Organismes.csv si absent
                                if not df_organismes[df_organismes["siret"] == siret].any().any():
                                    df_organismes = pd.concat(
                                        [df_organismes, pd.DataFrame([{"siret": siret, "nom": nom}])],
                                        ignore_index=True
                                    )
                            else:
                                # Ajouter aux fichiers sans SIRET
                                if row_result["evaluateur"]:
                                    evaluateurs_sans_siret.append({"code_rep": code, "nom": nom})
                                if row_result["formateur"]:
                                    formateurs_sans_siret.append({"code_rep": code, "nom": nom})
                                organismes_sans_siret.append({"nom": nom})
                                certificateurs_sans_siret.append({"code_rep": code, "nom": nom})

                        # Enregistrer dans un fichier CSV
                        output_file = os.path.join(output_dir, f"{type_}-{code}.csv")
                        df_result.to_csv(output_file, index=False)
                        print(f"Enregistré : {output_file}")
                    else:
                        print(f"Colonnes manquantes dans le fichier Excel pour {code}/{type_}")
            else:
                print(f"Aucun lien trouvé pour {code}/{type_}")
        except requests.RequestException as e:
            print(f"Erreur lors de la récupération de {url} : {e}")
        except Exception as e:
            print(f"Erreur lors du traitement de {code}/{type_} : {e}")

        # Ajouter un délai aléatoire entre 2 et 5 secondes
        time.sleep(random.uniform(2, 5))

    # Exporter les fichiers finaux
    pd.DataFrame(evaluateurs).to_csv(os.path.join(output_dir, "Evaluateurs.csv"), index=False)
    pd.DataFrame(formateurs).to_csv(os.path.join(output_dir, "Formateurs.csv"), index=False)
    pd.DataFrame(evaluateurs_sans_siret).to_csv(os.path.join(output_dir, "Evaluateurs_sans_siret.csv"), index=False)
    pd.DataFrame(formateurs_sans_siret).to_csv(os.path.join(output_dir, "Formateurs_sans_siret.csv"), index=False)
    pd.DataFrame(organismes_sans_siret).to_csv(os.path.join(output_dir, "Organismes_sans_siret.csv"), index=False)
    pd.DataFrame(certificateurs_sans_siret).to_csv(os.path.join(output_dir, "Certificateurs_sans_siret.csv"), index=False)
    df_organismes.to_csv(organismes_csv, index=False)

    # Calculer et afficher le temps total d'exécution
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Temps total d'exécution : {elapsed_time:.2f} secondes")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python scrape_organismes.py <dossier_csv>")
        sys.exit(1)
    csv_dir = sys.argv[1]
    repertoires_csv = f"{csv_dir}/Repertoires.csv"
    output_dir = csv_dir
    organismes_csv = f"{csv_dir}/Organismes.csv"
    # Lancer le scraping
    scrape_organismes(repertoires_csv, output_dir, organismes_csv)
