import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from create_database import Base, NSF, ROME, Forma, Organismes, Repertoires, RepertoiresNSF, RepertoiresROME, RepertoiresForma, Certificateurs, Evaluateurs, Formateurs
from sqlalchemy.dialects.sqlite import insert
from datetime import datetime

def populate_table(session, model, csv_path):
    """
    Peupler une table à partir d'un fichier CSV.
    Args:
        session: Session SQLAlchemy.
        model: Modèle SQLAlchemy correspondant à la table.
        csv_path: Chemin vers le fichier CSV.
    """

    """
    df = pd.read_csv(csv_path)
    records = df.to_dict(orient="records")
    session.bulk_insert_mappings(model, records)
    session.commit()
    print(f"Table {model.__tablename__} peuplée avec succès depuis {csv_path}.")"""

    df = pd.read_csv(csv_path)
    
    # Adaptation spécifique pour les dates si le modèle contient 'date_de_fin'
    if 'date_de_fin' in df.columns:
        df['date_de_fin'] = pd.to_datetime(df['date_de_fin'], errors='coerce').dt.date

    try:
        for record in df.to_dict(orient="records"):
            stmt = insert(model).values(**record).prefix_with("OR IGNORE")
            session.execute(stmt)
        session.commit()
        print(f"Table {model.__tablename__} peuplée avec succès depuis {csv_path}.")
    except Exception as e:
        session.rollback()
        print(f"Erreur lors du peuplement de {model.__tablename__} : {e}")    

def populate_database(db_path, csv_dir):
    """
    Peupler la base de données SQLite avec les fichiers CSV.
    Args:
        db_path (str): Chemin vers le fichier SQLite.
        csv_dir (str): Dossier contenant les fichiers CSV.
    """
    # Connexion à la base de données
    engine = create_engine(f'sqlite:///{db_path}')
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Peupler les tables indépendantes
        populate_table(session, NSF, f"{csv_dir}/NSF.csv")
        populate_table(session, ROME, f"{csv_dir}/ROME.csv")
        populate_table(session, Forma, f"{csv_dir}/Forma.csv")
        populate_table(session, Organismes, f"{csv_dir}/Organismes.csv")
        populate_table(session, Repertoires, f"{csv_dir}/Repertoires.csv")

        # Peupler les tables relationnelles
        populate_table(session, RepertoiresNSF, f"{csv_dir}/Repertoires_NSF.csv")
        populate_table(session, RepertoiresROME, f"{csv_dir}/Repertoires_Rome.csv")
        populate_table(session, RepertoiresForma, f"{csv_dir}/Repertoires_Forma.csv")
        populate_table(session, Certificateurs, f"{csv_dir}/Certificateurs.csv")
        populate_table(session, Evaluateurs, f"{csv_dir}/Evaluateurs.csv")
        populate_table(session, Formateurs, f"{csv_dir}/Formateurs.csv")

        print("Base de données peuplée avec succès.")
    except Exception as e:
        print(f"Erreur lors du peuplement de la base de données : {e}")
    finally:
        session.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python populate_database.py <dossier_csv>")
        sys.exit(1)
    db_path = "/home/tahtoh/RNCP-database/rncp_database.sqlite"
    csv_dir = sys.argv[1]
    populate_database(db_path, csv_dir)
