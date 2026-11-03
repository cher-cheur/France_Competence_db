"""Modèle relationnel de la base RNCP / RS (export open data France Compétences).

Toutes les tables sont reliées par `numero_fiche` (ex. "RNCP35288", "RS5487"),
qui est unique sur l'ensemble des deux répertoires : un même numéro peut exister
en RNCP et en RS, d'où l'usage de l'identifiant complet comme clé.
"""

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    event,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base

Base = declarative_base()


def fiche_fk(primary_key: bool = True) -> Column:
    return Column(
        String(20),
        ForeignKey("fiches.numero_fiche", ondelete="CASCADE"),
        primary_key=primary_key,
        nullable=False,
    )


# --- Fiches -----------------------------------------------------------------

class Fiche(Base):
    __tablename__ = "fiches"
    numero_fiche = Column(String(20), primary_key=True)  # "RNCP35288"
    type = Column(String(4), nullable=False, index=True)  # "RNCP" | "RS"
    numero = Column(Integer, nullable=False)  # 35288
    id_fiche = Column(Integer, unique=True)  # identifiant interne France Compétences
    intitule = Column(Text, nullable=False)
    abrege_libelle = Column(String(100))  # "MASTER", "TP", ...
    abrege_intitule = Column(Text)
    niveau = Column(Integer, index=True)  # 3..8, NULL si sans niveau (RS notamment)
    niveau_intitule = Column(Text)
    type_enregistrement = Column(String(50))  # "Enregistrement de droit" | "sur demande"
    validation_partielle = Column(Boolean)
    accessible_nouvelle_caledonie = Column(Boolean)
    accessible_polynesie_francaise = Column(Boolean)
    date_dernier_jo = Column(Date)
    date_decision = Column(Date)
    date_fin_enregistrement = Column(Date, index=True)
    date_effet = Column(Date)
    actif = Column(Boolean, nullable=False, index=True)
    # Déduit des voies d'accès ("En contrat d'apprentissage")
    apprentissage = Column(Boolean, nullable=False, default=False)


# --- Organismes ---------------------------------------------------------------

class Organisme(Base):
    __tablename__ = "organismes"
    siret = Column(String(14), primary_key=True)  # texte : conserve les zéros initiaux
    nom = Column(Text, nullable=False)


class Certificateur(Base):
    __tablename__ = "certificateurs"
    numero_fiche = fiche_fk()
    siret = Column(String(14), ForeignKey("organismes.siret", ondelete="CASCADE"), primary_key=True)


class Partenaire(Base):
    """Organisme habilité par le certificateur à préparer et/ou évaluer."""

    __tablename__ = "partenaires"
    numero_fiche = fiche_fk()
    siret = Column(String(14), ForeignKey("organismes.siret", ondelete="CASCADE"), primary_key=True, index=True)
    # HABILITATION_ORGA_FORM | HABILITATION_FORMER | HABILITATION_ORGANISER
    habilitation = Column(String(30), nullable=False)
    peut_former = Column(Boolean, nullable=False)
    peut_evaluer = Column(Boolean, nullable=False)


class PartenaireSansSiret(Base):
    __tablename__ = "partenaires_sans_siret"
    id = Column(Integer, primary_key=True, autoincrement=True)
    numero_fiche = fiche_fk(primary_key=False)
    nom = Column(Text, nullable=False)
    habilitation = Column(String(30), nullable=False)


# --- Contenu des fiches -------------------------------------------------------

class BlocCompetences(Base):
    __tablename__ = "blocs_competences"
    code = Column(String(30), primary_key=True)  # "RNCP35288BC01"
    numero_fiche = fiche_fk(primary_key=False)
    libelle = Column(Text, nullable=False)


class VoieAcces(Base):
    __tablename__ = "voies_acces"
    numero_fiche = fiche_fk()
    voie = Column(String(120), primary_key=True)


class Filiation(Base):
    """Lien ancienne certification -> nouvelle certification (remplacement)."""

    __tablename__ = "filiations"
    ancienne = Column(String(20), primary_key=True)
    nouvelle = Column(String(20), primary_key=True)


# --- Nomenclatures et liaisons --------------------------------------------------

class Rome(Base):
    __tablename__ = "rome"
    code = Column(String(10), primary_key=True)
    libelle = Column(Text, nullable=False)


class Nsf(Base):
    __tablename__ = "nsf"
    code = Column(String(10), primary_key=True)
    libelle = Column(Text, nullable=False)


class Formacode(Base):
    __tablename__ = "formacode"
    code = Column(String(10), primary_key=True)
    libelle = Column(Text, nullable=False)


class Ccn(Base):
    __tablename__ = "ccn"
    numero = Column(String(10), primary_key=True)
    libelle = Column(Text, nullable=False)


class FicheRome(Base):
    __tablename__ = "fiches_rome"
    numero_fiche = fiche_fk()
    code_rome = Column(String(10), ForeignKey("rome.code", ondelete="CASCADE"), primary_key=True, index=True)


class FicheNsf(Base):
    __tablename__ = "fiches_nsf"
    numero_fiche = fiche_fk()
    code_nsf = Column(String(10), ForeignKey("nsf.code", ondelete="CASCADE"), primary_key=True, index=True)


class FicheFormacode(Base):
    __tablename__ = "fiches_formacode"
    numero_fiche = fiche_fk()
    code_formacode = Column(String(10), ForeignKey("formacode.code", ondelete="CASCADE"), primary_key=True, index=True)


class FicheCcn(Base):
    __tablename__ = "fiches_ccn"
    numero_fiche = fiche_fk()
    numero_ccn = Column(String(10), ForeignKey("ccn.numero", ondelete="CASCADE"), primary_key=True)


# --- Métadonnées ----------------------------------------------------------------

class Chargement(Base):
    __tablename__ = "chargements"
    id = Column(Integer, primary_key=True, autoincrement=True)
    date_export = Column(Date, nullable=False)
    fichier_source = Column(Text, nullable=False)
    charge_le = Column(DateTime, nullable=False)


@event.listens_for(Engine, "connect")
def _sqlite_foreign_keys(dbapi_connection, _record):
    if dbapi_connection.__class__.__module__.startswith("sqlite3"):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")


def get_engine(db_path: str) -> Engine:
    return create_engine(f"sqlite:///{db_path}")


def create_schema(engine: Engine, reset: bool = False) -> None:
    if reset:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
