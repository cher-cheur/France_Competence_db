import pandas as pd
import re
import sys
import os

def extract_repertoires(df_active: pd.DataFrame) -> pd.DataFrame:
    """
    Extrait la table Repertoires à partir des données filtrées.
    """
    return pd.DataFrame({
        "code": df_active["Code RNCP/RS"].str.extract(r'(\d+)')[0],
        "type": df_active["Type de répertoire"],
        "titre": df_active["Intitulé"],
        "niveau": df_active["Niveau de qualification"].str.replace("Niveau ", "", regex=False),
        "date_de_fin": df_active["Date d'échéance de l'enregistrement"],
        "apprentissage": df_active["Ouverture à l'apprentissage"].astype(bool)
    })

def extract_ecoles(df_active: pd.DataFrame) -> (pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame):
    """
    Extrait quatre tables :
    - Organismes : contient les colonnes 'siret' et 'nom'.
    - Certificateur : contient les colonnes 'code_rep' (code RNCP/RS sans le string) et 'siret'.
    - Organismes_sans_siret : contient les organismes sans SIRET.
    - Certificateurs_sans_siret : contient les certificateurs sans SIRET.

    Args:
        df_active (pd.DataFrame): DataFrame filtré avec les données actives.

    Returns:
        (pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame): Quatre DataFrames.
    """
    organismes, certificateur = [], []
    organismes_sans_siret, certificateurs_sans_siret = [], []

    for _, row in df_active.iterrows():
        # Extraire le code_rep de la colonne "Code RNCP/RS"
        code_rep_match = re.search(r'(\d+)', str(row.get("Code RNCP/RS", "")))
        if code_rep_match:
            code_rep = code_rep_match.group(1).strip()

            # Extraire les certificateurs
            certificateurs = str(row.get("Certificateurs", "")).split(", ")  # Séparer les valeurs par des virgules
            for cert in certificateurs:
                if " - " in cert:  # Vérifier si la valeur contient " - "
                    parts = cert.split(" - ")
                    if len(parts) > 1:  # S'assurer qu'il y a un SIRET
                        nom = " - ".join(parts[:-1]).strip()
                        siret = parts[-1].strip()
                        if siret.isdigit():  # Inclure uniquement si le SIRET est un nombre
                            # Ajouter à la table 'organismes'
                            if not any(org["siret"] == siret for org in organismes):  # Éviter les doublons
                                organismes.append({
                                    "siret": int(siret),
                                    "nom": nom
                                })
                            # Ajouter à la table 'certificateur'
                            certificateur.append({
                                "code_rep": code_rep,
                                "siret": int(siret)
                            })
                        else:
                            # Ajouter aux fichiers sans SIRET
                            organismes_sans_siret.append({"nom": nom})
                            certificateurs_sans_siret.append({"code_rep": code_rep, "nom": nom})

    return (
        pd.DataFrame(organismes),
        pd.DataFrame(certificateur),
        pd.DataFrame(organismes_sans_siret),
        pd.DataFrame(certificateurs_sans_siret),
    )

def extract_nsf(df_active: pd.DataFrame) -> pd.DataFrame:
    """
    Extrait la table NSF à partir des données filtrées en utilisant une logique basée sur les chiffres.
    """
    nsf = []
    for _, row in df_active.iterrows():
        nsf_values = str(row.get("Code(s) NSF", ""))
        # Trouver les positions des débuts de chaque code (séquences de chiffres et lettres)
        matches = list(re.finditer(r'\b\d+\w*\b', nsf_values))
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(nsf_values)
            segment = nsf_values[start:end].strip()
            if " : " in segment:  # Vérifier si le segment contient " : "
                code, nom = segment.split(" : ", 1)
                code = code.strip()
                nom = nom.strip().strip('"').rstrip(",")  # Supprimer les guillemets et la virgule finale
                if not any(entry["code"] == code and entry["nom"] == nom for entry in nsf):  # Éviter les doublons
                    nsf.append({
                        "code": code,
                        "nom": nom
                    })
    return pd.DataFrame(nsf)

def extract_rome(df_active: pd.DataFrame) -> pd.DataFrame:
    """
    Extrait la table ROME à partir des données filtrées.
    """
    rome = []
    for _, row in df_active.iterrows():
        rome_values = str(row.get("Code(s) ROME", "")).split(", ")  # Séparer les valeurs par des virgules
        for value in rome_values:
            if " : " in value:  # Vérifier si la valeur contient " : "
                code, nom = value.split(" : ", 1)  # Décomposer en code et nom
                code = code.strip()
                nom = nom.strip()
                if not any(entry["code"] == code for entry in rome):  # Éviter les doublons
                    rome.append({
                        "code": code,
                        "nom": nom
                    })
    return pd.DataFrame(rome)

def extract_forma(df_active: pd.DataFrame) -> pd.DataFrame:
    """
    Extrait la table Forma à partir des données filtrées.
    """
    forma = []
    for _, row in df_active.iterrows():
        forma_values = str(row.get("Formacode(s)", "")).split(", ")  # Séparer les valeurs par des virgules
        for value in forma_values:
            if " : " in value:  # Vérifier si la valeur contient " : "
                code, nom = value.split(" : ", 1)  # Décomposer en code et nom
                code = code.strip()
                nom = nom.strip()
                if not any(entry["code"] == code for entry in forma):  # Éviter les doublons
                    forma.append({
                        "code": code,
                        "nom": nom
                    })
    return pd.DataFrame(forma)

def extract_repertoires_nsf(df_active: pd.DataFrame) -> pd.DataFrame:
    """
    Extrait la table Repertoires_NSF à partir des données filtrées.
    """
    repertoires_nsf = []
    for _, row in df_active.iterrows():
        # Extraire le code_rep de la colonne "Code RNCP/RS"
        code_rep_match = re.search(r'(\d+)', str(row.get("Code RNCP/RS", "")))
        if code_rep_match:
            code_rep = code_rep_match.group(1).strip()

            # Extraire les codes NSF de la colonne "Code(s) NSF"
            nsf_values = str(row.get("Code(s) NSF", ""))
            matches = list(re.finditer(r'\b\d+\w*\b', nsf_values))
            for i, match in enumerate(matches):
                start = match.start()
                end = matches[i + 1].start() if i + 1 < len(matches) else len(nsf_values)
                segment = nsf_values[start:end].strip()
                if " : " in segment:  # Vérifier si le segment contient " : "
                    code_nsf, _ = segment.split(" : ", 1)
                    code_nsf = code_nsf.strip()
                    repertoires_nsf.append({
                        "code_rep": code_rep,
                        "code_nsf": code_nsf
                    })
    return pd.DataFrame(repertoires_nsf)

def extract_repertoires_rome(df_active: pd.DataFrame) -> pd.DataFrame:
    """
    Extrait la table Repertoires_Rome à partir des données filtrées.
    """
    repertoires_rome = []
    for _, row in df_active.iterrows():
        # Extraire le code_rep de la colonne "Code RNCP/RS"
        code_rep_match = re.search(r'(\d+)', str(row.get("Code RNCP/RS", "")))
        if code_rep_match:
            code_rep = code_rep_match.group(1).strip()

            # Extraire les codes ROME de la colonne "Code(s) ROME"
            rome_values = str(row.get("Code(s) ROME", ""))
            rome_matches = rome_values.split(", ")  # Séparer les valeurs par des virgules
            for rome in rome_matches:
                if " : " in rome:  # Vérifier si le segment contient " : "
                    code_rome, _ = rome.split(" : ", 1)
                    code_rome = code_rome.strip()
                    repertoires_rome.append({
                        "code_rep": code_rep,
                        "code_rome": code_rome
                    })
    return pd.DataFrame(repertoires_rome)

def extract_repertoires_forma(df_active: pd.DataFrame) -> pd.DataFrame:
    """
    Extrait la table Repertoires_Forma à partir des données filtrées.
    """
    repertoires_forma = []
    for _, row in df_active.iterrows():
        # Extraire le code_rep de la colonne "Code RNCP/RS"
        code_rep_match = re.search(r'(\d+)', str(row.get("Code RNCP/RS", "")))
        if code_rep_match:
            code_rep = code_rep_match.group(1).strip()

            # Extraire les codes Formacode de la colonne "Formacode(s)"
            forma_values = str(row.get("Formacode(s)", ""))
            forma_matches = forma_values.split(", ")  # Séparer les valeurs par des virgules
            for forma in forma_matches:
                if " : " in forma:  # Vérifier si le segment contient " : "
                    code_forma, _ = forma.split(" : ", 1)
                    code_forma = code_forma.strip()
                    repertoires_forma.append({
                        "code_rep": code_rep,
                        "code_forma": code_forma
                    })
    return pd.DataFrame(repertoires_forma)

def extract_repertoires_siret(df_active: pd.DataFrame) -> pd.DataFrame:
    """
    Extrait la table Repertoires_Siret à partir des données filtrées, en incluant uniquement les SIRET valides.
    """
    repertoires_siret = []
    for _, row in df_active.iterrows():
        # Extraire le code_rep de la colonne "Code RNCP/RS"
        code_rep_match = re.search(r'(\d+)', str(row.get("Code RNCP/RS", "")))
        if code_rep_match:
            code_rep = code_rep_match.group(1).strip()

            # Extraire les sirets de la colonne "Certificateurs"
            certificateurs = str(row.get("Certificateurs", "")).split(", ")  # Séparer les valeurs par des virgules
            for cert in certificateurs:
                if " - " in cert:  # Vérifier si la valeur contient " - "
                    parts = cert.split(" - ")
                    if len(parts) > 1:  # S'assurer qu'il y a un siret
                        siret = parts[-1].strip()
                        if siret.isdigit():  # Inclure uniquement si le SIRET est un nombre
                            repertoires_siret.append({
                                "code_rep": code_rep,
                                "siret": siret
                            })
    return pd.DataFrame(repertoires_siret)

def process_excel(file_path: str, output_dir: str):
    """
    Lit un fichier Excel, filtre les données actives, et génère plusieurs tables.
    """
    # Lire le fichier Excel
    df = pd.read_excel(file_path)

    # Filtrer les lignes avec "Statut" égal à "Active"
    df_active = df[df["Statut"] == "Active"]

    # Extraire les tables
    
    df_repertoires = extract_repertoires(df_active)
    
    df_nsf = extract_nsf(df_active)
    df_rome = extract_rome(df_active)
    df_forma = extract_forma(df_active)
    df_repertoires_nsf = extract_repertoires_nsf(df_active)
    df_repertoires_rome = extract_repertoires_rome(df_active)
    df_repertoires_forma = extract_repertoires_forma(df_active)
    df_repertoires_siret = extract_repertoires_siret(df_active)
    df_ecoles, df_certificateur, df_organismes_sans_siret, df_certificateurs_sans_siret = extract_ecoles(df_active)

    os.makedirs(output_dir, exist_ok=True)

    # Exporter les tableaux en fichiers CSV
    df_repertoires.to_csv(f"{output_dir}/Repertoires.csv", index=False)
    df_nsf.to_csv(f"{output_dir}/NSF.csv", index=False)
    df_rome.to_csv(f"{output_dir}/ROME.csv", index=False)
    df_forma.to_csv(f"{output_dir}/Forma.csv", index=False)
    df_repertoires_nsf.to_csv(f"{output_dir}/Repertoires_NSF.csv", index=False)
    df_repertoires_rome.to_csv(f"{output_dir}/Repertoires_Rome.csv", index=False)
    df_repertoires_forma.to_csv(f"{output_dir}/Repertoires_Forma.csv", index=False)
    df_repertoires_siret.to_csv(f"{output_dir}/Repertoires_Siret.csv", index=False)
    df_ecoles.to_csv(f"{output_dir}/Organismes.csv", index=False)
    df_certificateur.to_csv(f"{output_dir}/Certificateurs.csv", index=False)
    df_organismes_sans_siret.to_csv(f"{output_dir}/Organismes_sans_siret.csv", index=False)
    df_certificateurs_sans_siret.to_csv(f"{output_dir}/Certificateurs_sans_siret.csv", index=False)
    


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python process_excel.py <chemin_fichier_excel> <dossier_csv>")
        sys.exit(1)
    process_excel(sys.argv[1], sys.argv[2])
