"""Chargement de l'export CSV RNCP/RS dans une base SQLite.

La base est reconstruite intégralement à chaque chargement (l'export est un
instantané complet), dans un fichier temporaire remplacé à la fin : en cas
d'erreur, la base précédente reste intacte.
"""

import argparse
import os
import re
import unicodedata
import zipfile
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from schema import create_schema, get_engine

SIRET_RE = r"\d{14}"
BOOL_MAP = {"Oui": True, "Non": False}
APPRENTISSAGE = "En contrat d’apprentissage"
# Habilitation -> (peut_former, peut_evaluer)
HABILITATIONS = {
    "HABILITATION_ORGA_FORM": (True, True),
    "HABILITATION_FORMER": (True, False),
    "HABILITATION_ORGANISER": (False, True),
}


# --- Lecture --------------------------------------------------------------------

def _normalize(name: str) -> str:
    return unicodedata.normalize("NFC", name).lower()


def read_member(zf: zipfile.ZipFile, key: str) -> pd.DataFrame:
    """Lit le fichier `export_fiches_CSV_<key>_AAAA_MM_JJ.csv` de l'archive."""
    pattern = re.compile(rf"export_fiches_csv_{re.escape(_normalize(key))}_\d{{4}}_\d{{2}}_\d{{2}}\.csv$")
    matches = [n for n in zf.namelist() if pattern.search(_normalize(n))]
    if len(matches) != 1:
        raise FileNotFoundError(f"Fichier '{key}' introuvable (ou ambigu) dans l'archive : {matches}")
    with zf.open(matches[0]) as fh:
        df = pd.read_csv(fh, sep=";", dtype=str, keep_default_na=False, encoding="utf-8")
    # Les SIRET sont préfixés d'une tabulation ; on nettoie toutes les cellules.
    return df.apply(lambda col: col.str.strip())


def _dates(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, format="%d/%m/%Y", errors="coerce")
    return parsed.dt.date.astype(object).where(parsed.notna(), None)


def _bools(series: pd.Series) -> pd.Series:
    return series.map(BOOL_MAP).astype(object).where(series.isin(BOOL_MAP), None)


# --- Transformations ------------------------------------------------------------

def build_tables(zf: zipfile.ZipFile) -> dict[str, pd.DataFrame]:
    tables: dict[str, pd.DataFrame] = {}

    # Voies d'accès (sert aussi à déduire l'apprentissage)
    voies = read_member(zf, "VoixdAccès").rename(columns={"Numero_Fiche": "numero_fiche", "Si_Jury": "voie"})
    voies = voies[voies.voie != ""].drop_duplicates()
    fiches_apprentissage = set(voies.loc[voies.voie == APPRENTISSAGE, "numero_fiche"])

    # Fiches
    std = read_member(zf, "Standard")
    parts = std.Numero_Fiche.str.extract(r"^(RNCP|RS)(\d+)$")
    if parts[0].isna().any():
        bad = std.Numero_Fiche[parts[0].isna()].tolist()[:5]
        raise ValueError(f"Numéros de fiche inattendus : {bad}")
    fiches = pd.DataFrame({
        "numero_fiche": std.Numero_Fiche,
        "type": parts[0],
        "numero": parts[1].astype(int),
        "id_fiche": pd.to_numeric(std.Id_Fiche, errors="coerce").astype("Int64"),
        "intitule": std.Intitule,
        "abrege_libelle": std.Abrege_Libelle.replace("", None),
        "abrege_intitule": std.Abrege_Intitule.replace("", None),
        "niveau": pd.to_numeric(std.Nomenclature_Europe_Niveau.str.extract(r"NIV(\d)")[0], errors="coerce").astype("Int64"),
        "niveau_intitule": std.Nomenclature_Europe_Intitule.replace("", None),
        "type_enregistrement": std.Type_Enregistrement.replace("", None),
        "validation_partielle": _bools(std.Validation_Partielle),
        "accessible_nouvelle_caledonie": _bools(std.Accessible_Nouvelle_Caledonie),
        "accessible_polynesie_francaise": _bools(std.Accessible_Polynesie_Francaise),
        "date_dernier_jo": _dates(std.Date_dernier_jo),
        "date_decision": _dates(std.Date_Decision),
        "date_fin_enregistrement": _dates(std.Date_Fin_Enregistrement),
        "date_effet": _dates(std.Date_Effet),
        "actif": std.Actif.eq("ACTIVE"),
        "apprentissage": std.Numero_Fiche.isin(fiches_apprentissage),
    })
    tables["fiches"] = fiches
    known = set(fiches.numero_fiche)
    tables["voies_acces"] = voies[voies.numero_fiche.isin(known)]

    # Organismes : certificateurs + partenaires
    cert = read_member(zf, "Certificateurs").rename(columns={
        "Numero_Fiche": "numero_fiche", "Siret_Certificateur": "siret", "Nom_Certificateur": "nom"})
    part = read_member(zf, "Partenaires").rename(columns={
        "Numero_Fiche": "numero_fiche", "Siret_Partenaire": "siret",
        "Nom_Partenaire": "nom", "Habilitation_Partenaire": "habilitation"})
    cert = cert[cert.numero_fiche.isin(known)]
    part = part[part.numero_fiche.isin(known)]

    cert_ok = cert[cert.siret.str.fullmatch(SIRET_RE)]
    if len(cert_ok) < len(cert):
        print(f"  {len(cert) - len(cert_ok)} certificateur(s) sans SIRET valide ignoré(s)")
    part_ok = part[part.siret.str.fullmatch(SIRET_RE)]

    organismes = pd.concat([cert_ok[["siret", "nom"]], part_ok[["siret", "nom"]]])
    tables["organismes"] = organismes[organismes.nom != ""].drop_duplicates("siret")
    tables["certificateurs"] = cert_ok[["numero_fiche", "siret"]].drop_duplicates()

    unknown = set(part.habilitation) - set(HABILITATIONS)
    if unknown:
        print(f"  Habilitation(s) inconnue(s), traitée(s) sans droits : {sorted(unknown)}")
    droits = part_ok.habilitation.map(lambda h: HABILITATIONS.get(h, (False, False)))
    tables["partenaires"] = part_ok.assign(
        peut_former=[d[0] for d in droits], peut_evaluer=[d[1] for d in droits],
    )[["numero_fiche", "siret", "habilitation", "peut_former", "peut_evaluer"]].drop_duplicates(["numero_fiche", "siret"])
    tables["partenaires_sans_siret"] = part[~part.siret.str.fullmatch(SIRET_RE)][["numero_fiche", "nom", "habilitation"]]

    # Blocs de compétences
    blocs = read_member(zf, "Blocs_De_Compétences").rename(columns={
        "Numero_Fiche": "numero_fiche", "Bloc_Competences_Code": "code", "Bloc_Competences_Libelle": "libelle"})
    tables["blocs_competences"] = blocs[blocs.numero_fiche.isin(known) & (blocs.code != "")].drop_duplicates("code")[
        ["code", "numero_fiche", "libelle"]]

    # Nomenclatures simples
    for key, code_col, label_col, nomenclature, link, link_col in [
        ("Rome", "Codes_Rome_Code", "Codes_Rome_Libelle", "rome", "fiches_rome", "code_rome"),
        ("Nsf", "Nsf_Code", "Nsf_Intitule", "nsf", "fiches_nsf", "code_nsf"),
        ("Formacode", "Formacode_Code", "Formacode_Libelle", "formacode", "fiches_formacode", "code_formacode"),
    ]:
        df = read_member(zf, key)
        df = df[df.Numero_Fiche.isin(known) & (df[code_col] != "")]
        # Les libellés ROME de l'export ont des apostrophes doublées ("d''information").
        df[label_col] = df[label_col].str.replace("''", "'", regex=False)
        tables[nomenclature] = (df[[code_col, label_col]].drop_duplicates(code_col)
                                .rename(columns={code_col: "code", label_col: "libelle"}))
        tables[link] = (df[["Numero_Fiche", code_col]].drop_duplicates()
                        .rename(columns={"Numero_Fiche": "numero_fiche", code_col: link_col}))

    # Conventions collectives (jusqu'à 3 colonnes par fiche)
    ccn = read_member(zf, "CCN")
    ccn_long = pd.concat([
        ccn[["Numero_Fiche", f"Ccn_{i}_Numero", f"Ccn_{i}_Libelle"]].set_axis(["numero_fiche", "numero_ccn", "libelle"], axis=1)
        for i in (1, 2, 3)
    ])
    ccn_long = ccn_long[ccn_long.numero_fiche.isin(known) & (ccn_long.numero_ccn != "")]
    tables["ccn"] = ccn_long[["numero_ccn", "libelle"]].drop_duplicates("numero_ccn").rename(columns={"numero_ccn": "numero"})
    tables["fiches_ccn"] = ccn_long[["numero_fiche", "numero_ccn"]].drop_duplicates()

    # Filiations : chaque ligne relie la fiche à son prédécesseur et/ou son successeur
    fil = read_member(zf, "Ancienne_Nouvelle_Certification")
    edges = pd.concat([
        fil.loc[fil.Ancienne_Certification != "", ["Ancienne_Certification", "Numero_Fiche"]].set_axis(["ancienne", "nouvelle"], axis=1),
        fil.loc[fil.Nouvelle_Certification != "", ["Numero_Fiche", "Nouvelle_Certification"]].set_axis(["ancienne", "nouvelle"], axis=1),
    ])
    tables["filiations"] = edges[edges.ancienne != edges.nouvelle].drop_duplicates()

    return tables


# Ordre d'insertion compatible avec les clés étrangères
LOAD_ORDER = [
    "fiches", "organismes", "rome", "nsf", "formacode", "ccn",
    "certificateurs", "partenaires", "partenaires_sans_siret", "blocs_competences",
    "voies_acces", "filiations", "fiches_rome", "fiches_nsf", "fiches_formacode", "fiches_ccn",
]


def export_date_from_name(path: Path) -> date:
    match = re.search(r"(\d{4}-\d{2}-\d{2})", path.name)
    return date.fromisoformat(match.group(1)) if match else date.today()


def load_database(zip_path: Path, db_path: Path) -> dict[str, int]:
    """Construit la base à partir de l'archive et retourne le nombre de lignes par table."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = db_path.with_name(db_path.name + ".tmp")
    tmp_path.unlink(missing_ok=True)

    with zipfile.ZipFile(zip_path) as zf:
        tables = build_tables(zf)

    engine = get_engine(str(tmp_path))
    try:
        create_schema(engine)
        with engine.begin() as conn:
            for name in LOAD_ORDER:
                tables[name].to_sql(name, conn, if_exists="append", index=False, chunksize=5000)
            pd.DataFrame([{
                "date_export": export_date_from_name(zip_path),
                "fichier_source": zip_path.name,
                "charge_le": datetime.now(),
            }]).to_sql("chargements", conn, if_exists="append", index=False)
    except Exception:
        engine.dispose()
        tmp_path.unlink(missing_ok=True)
        raise
    engine.dispose()
    os.replace(tmp_path, db_path)

    counts = {name: len(tables[name]) for name in LOAD_ORDER}
    for name, count in counts.items():
        print(f"  {name:<24} {count:>8}")
    print(f"Base enregistrée : {db_path}")
    return counts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip_path", type=Path, help="Archive export-fiches-csv-AAAA-MM-JJ.zip")
    parser.add_argument("--db", type=Path, default=Path("data/rncp.sqlite"))
    args = parser.parse_args()
    load_database(args.zip_path, args.db)
