"""Pipeline complet : téléchargement de l'export open data puis construction de la base."""

import argparse
from datetime import date
from pathlib import Path

from download import download_csv_export
from load import load_database


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"), help="Dossier des exports téléchargés")
    parser.add_argument("--db", type=Path, default=Path("data/rncp.sqlite"), help="Base SQLite à produire")
    parser.add_argument("--date", type=date.fromisoformat, help="Date de l'export AAAA-MM-JJ (défaut : le plus récent)")
    parser.add_argument("--zip", type=Path, help="Utiliser une archive locale au lieu de télécharger")
    args = parser.parse_args()

    zip_path = args.zip if args.zip else download_csv_export(args.data_dir, args.date)[1]
    load_database(zip_path, args.db)


if __name__ == "__main__":
    main()
