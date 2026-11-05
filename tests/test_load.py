"""Tests du chargement sur une petite archive reproduisant le format de l'export."""

import sqlite3
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from load import load_database  # noqa: E402

SUFFIX = "2026_11_02"

FILES = {
    "Standard": [
        '"Id_Fiche";"Numero_Fiche";"Intitule";"Abrege_Libelle";"Abrege_Intitule";"Nomenclature_Europe_Niveau";'
        '"Nomenclature_Europe_Intitule";"Accessible_Nouvelle_Caledonie";"Accessible_Polynesie_Francaise";'
        '"Date_dernier_jo";"Date_Decision";"Date_Fin_Enregistrement";"Date_Effet";"Type_Enregistrement";'
        '"Validation_Partielle";"Actif"',
        '"1";"RNCP100";"Data analyst";"TP";"Titre professionnel";"NIV6";"Niveau 6";"Non";"Non";;"01/02/2024";'
        '"01/02/2029";;"Enregistrement sur demande";"Oui";"ACTIVE"',
        # Même numéro en RS : ne doit pas écraser la fiche RNCP
        '"2";"RS100";"Intelligence artificielle\nen entreprise";;;;;"Non";"Non";;;"31/12/2027";;'
        '"Enregistrement sur demande";;"ACTIVE"',
        '"3";"RNCP50";"Ancien titre";;;"NIV5";"Niveau 5";"Non";"Non";;;"01/01/2020";;"Enregistrement de droit";;"INACTIVE"',
    ],
    "Certificateurs": [
        '"Numero_Fiche";"Siret_Certificateur";"Nom_Certificateur"',
        '"RNCP100";"\t01234567890123";"CERTIF SAS"',
    ],
    "Partenaires": [
        '"Numero_Fiche";"Nom_Partenaire";"Siret_Partenaire";"Habilitation_Partenaire"',
        '"RNCP100";"ECOLE A";"\t11111111111111";"HABILITATION_ORGA_FORM"',
        '"RNCP100";"ECOLE B";"\t22222222222222";"HABILITATION_FORMER"',
        '"RS100";"ECOLE A";"\t11111111111111";"HABILITATION_ORGANISER"',
        '"RS100";"ECOLE SANS SIRET";"";"HABILITATION_FORMER"',
    ],
    "Blocs_De_Compétences": [
        '"Numero_Fiche";"Bloc_Competences_Code";"Bloc_Competences_Libelle"',
        '"RNCP100";"RNCP100BC01";"Collecter les données"',
    ],
    "Rome": ['"Numero_Fiche";"Codes_Rome_Code";"Codes_Rome_Libelle"',
             '"RNCP100";"M1805";"Études et développement d\'\'information"'],
    "Nsf": ['"Numero_Fiche";"Nsf_Code";"Nsf_Intitule"', '"RNCP100";"326";"326 : Informatique"'],
    "Formacode": ['"Numero_Fiche";"Formacode_Code";"Formacode_Libelle"', '"RS100";"31025";"Analyse données"'],
    "CCN": [
        '"Numero_Fiche";"Ccn_1_Numero";"Ccn_1_Libelle";"Ccn_2_Numero";"Ccn_2_Libelle";"Ccn_3_Numero";"Ccn_3_Libelle"',
        '"RNCP100";"1486";"Syntec";"2120";"Banque";;',
    ],
    "VoixdAccès": [
        '"Numero_Fiche";"Si_Jury"',
        '"RNCP100";"En contrat d’apprentissage"',
        '"RNCP100";"Par expérience"',
        '"RS100";"Par expérience"',
    ],
    "Ancienne_Nouvelle_Certification": [
        '"Numero_Fiche";"Ancienne_Certification";"Nouvelle_Certification"',
        '"RNCP100";"RNCP50";',
        '"RNCP50";;"RNCP100"',
    ],
}


@pytest.fixture()
def db(tmp_path: Path) -> sqlite3.Connection:
    zip_path = tmp_path / "export-fiches-csv-2026-11-03.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for key, lines in FILES.items():
            zf.writestr(f"export_fiches_CSV_{key}_{SUFFIX}.csv", "\n".join(lines) + "\n")
    db_path = tmp_path / "rncp.sqlite"
    load_database(zip_path, db_path)
    conn = sqlite3.connect(db_path)
    yield conn
    conn.close()


def q(conn, sql, *params):
    return conn.execute(sql, params).fetchall()


def test_rncp_et_rs_de_meme_numero_coexistent(db):
    assert q(db, "SELECT numero_fiche, type, numero FROM fiches WHERE numero = 100 ORDER BY type") == [
        ("RNCP100", "RNCP", 100), ("RS100", "RS", 100)]


def test_champs_fiche(db):
    row = q(db, "SELECT niveau, date_fin_enregistrement, actif, apprentissage, validation_partielle "
                "FROM fiches WHERE numero_fiche = 'RNCP100'")[0]
    assert row == (6, "2029-02-01", 1, 1, 1)
    assert q(db, "SELECT niveau, apprentissage, intitule FROM fiches WHERE numero_fiche = 'RS100'") == [
        (None, 0, "Intelligence artificielle\nen entreprise")]


def test_siret_texte_avec_zero_initial(db):
    assert q(db, "SELECT siret FROM certificateurs") == [("01234567890123",)]


def test_partenaires_et_habilitations(db):
    rows = q(db, "SELECT numero_fiche, siret, peut_former, peut_evaluer FROM partenaires ORDER BY 1, 2")
    assert rows == [
        ("RNCP100", "11111111111111", 1, 1),
        ("RNCP100", "22222222222222", 1, 0),
        ("RS100", "11111111111111", 0, 1),
    ]
    assert q(db, "SELECT numero_fiche, nom FROM partenaires_sans_siret") == [("RS100", "ECOLE SANS SIRET")]
    assert q(db, "SELECT COUNT(*) FROM organismes") == [(3,)]


def test_tables_de_liaison(db):
    assert q(db, "SELECT code FROM blocs_competences") == [("RNCP100BC01",)]
    assert q(db, "SELECT numero_ccn FROM fiches_ccn ORDER BY 1") == [("1486",), ("2120",)]
    assert q(db, "SELECT ancienne, nouvelle FROM filiations") == [("RNCP50", "RNCP100")]
    assert q(db, "SELECT code_rome FROM fiches_rome") == [("M1805",)]
    assert q(db, "SELECT libelle FROM rome") == [("Études et développement d'information",)]


def test_integrite_et_metadonnees(db):
    assert q(db, "PRAGMA foreign_key_check") == []
    assert q(db, "SELECT date_export, fichier_source FROM chargements") == [
        ("2026-11-03", "export-fiches-csv-2026-11-03.zip")]
