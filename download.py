"""Téléchargement de l'export CSV quotidien RNCP/RS publié sur data.gouv.fr."""

import argparse
import re
import time
import zipfile
from datetime import date
from pathlib import Path

import requests

DATASET_ID = "5eebbc067a14b6fecc9c9976"
API_URL = f"https://www.data.gouv.fr/api/1/datasets/{DATASET_ID}/"
CSV_EXPORT_RE = re.compile(r"^export-fiches-csv-(\d{4}-\d{2}-\d{2})\.zip$")


def _get_with_retries(url: str, retries: int = 12, timeout: int = 120, **kwargs) -> requests.Response:
    delay = 2
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, timeout=timeout, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            if attempt == retries:
                raise
            print(f"  tentative {attempt}/{retries} échouée ({exc}), nouvel essai dans {delay}s")
            time.sleep(delay)
            delay = min(delay * 2, 30)
    raise AssertionError("unreachable")


def find_csv_export(export_date: date | None = None) -> tuple[date, str]:
    """Retourne (date, url) de l'export CSV demandé, ou du plus récent."""
    resources = _get_with_retries(API_URL).json()["resources"]
    exports = {}
    for resource in resources:
        match = CSV_EXPORT_RE.match(resource.get("title", ""))
        if match:
            exports[date.fromisoformat(match.group(1))] = resource["url"]
    if not exports:
        raise RuntimeError("Aucun export CSV trouvé dans le jeu de données data.gouv.fr")
    if export_date is None:
        export_date = max(exports)
    if export_date not in exports:
        raise RuntimeError(f"Pas d'export CSV pour le {export_date.isoformat()}")
    return export_date, exports[export_date]


def download_csv_export(data_dir: Path, export_date: date | None = None) -> tuple[date, Path]:
    """Télécharge l'export (s'il n'est pas déjà présent) et retourne (date, chemin du zip)."""
    export_date, url = find_csv_export(export_date)
    data_dir.mkdir(parents=True, exist_ok=True)
    target = data_dir / f"export-fiches-csv-{export_date.isoformat()}.zip"

    if target.exists() and zipfile.is_zipfile(target):
        print(f"Export déjà présent : {target}")
        return export_date, target

    print(f"Téléchargement de {url}")
    content = _get_with_retries(url, timeout=600).content
    tmp = target.with_suffix(".part")
    tmp.write_bytes(content)
    if not zipfile.is_zipfile(tmp):
        tmp.unlink()
        raise RuntimeError("Le fichier téléchargé n'est pas une archive zip valide")
    tmp.replace(target)
    print(f"Enregistré : {target} ({len(content) / 1e6:.1f} Mo)")
    return export_date, target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--date", type=date.fromisoformat, help="AAAA-MM-JJ (défaut : le plus récent)")
    args = parser.parse_args()
    download_csv_export(args.data_dir, args.date)
