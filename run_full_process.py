import subprocess
import sys
import os

def run_script(script_path, args=None):
    cmd = [sys.executable, script_path]
    if args:
        cmd += args
    print(f"Exécution de : {' '.join(cmd)}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"Erreur lors de l'exécution de {script_path}")
        sys.exit(result.returncode)

if __name__ == "__main__":
    # Créer le dossier csv4db s'il n'existe pas
    csv_dir = "/home/tahtoh/France_Competence_db/csv4db"
    os.makedirs(csv_dir, exist_ok=True)

    # Chemin du fichier Excel à traiter
    excel_file = "export-intelligence-artificielle.xlsx"

    # 1. Extraction et structuration depuis l'Excel
    run_script("/home/tahtoh/France_Competence_db/process_excel.py", [excel_file, csv_dir])

    # 2. Scraping des organismes partenaires
    run_script("/home/tahtoh/France_Competence_db/scrape_organismes.py", [csv_dir])

    # 3. Création de la base de données (si non existante)
    db_path = "/home/tahtoh/France_Competence_db/rncp_database.sqlite"
    if not os.path.exists(db_path):
        run_script("/home/tahtoh/France_Competence_db/create_database.py")
    else:
        print("La base de données existe déjà.")

    # 4. Peuplement de la base avec les CSV
    run_script("/home/tahtoh/France_Competence_db/populate_database.py", [csv_dir])

    print("Processus complet terminé avec succès.")
