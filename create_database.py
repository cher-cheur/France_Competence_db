from sqlalchemy import create_engine, Column, Integer, String, Boolean, Date, Enum, ForeignKey, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

# Table principale : repertoires
class Repertoires(Base):
    __tablename__ = 'repertoires'
    code = Column(Integer, primary_key=True)
    type = Column(Enum('RNCP', 'RS', name='type_enum'), nullable=False)
    titre = Column(String(255), nullable=False)
    niveau = Column(Integer)
    date_de_fin = Column(Date)
    apprentissage = Column(Boolean)

# Table principale : nsf
class NSF(Base):
    __tablename__ = 'nsf'
    code = Column(String(50), primary_key=True)
    nom = Column(String(255), nullable=False)

# Table principale : rome
class ROME(Base):
    __tablename__ = 'rome'
    code = Column(String(50), primary_key=True)
    nom = Column(String(255), nullable=False)

# Table principale : forma
class Forma(Base):
    __tablename__ = 'forma'
    code = Column(String(50), primary_key=True)
    nom = Column(String(255), nullable=False)

# Table principale : organismes
class Organismes(Base):
    __tablename__ = 'organismes'
    siret = Column(String(14), primary_key=True)
    nom = Column(String(255), nullable=False)

# Table de relation : repertoires_nsf
class RepertoiresNSF(Base):
    __tablename__ = 'repertoires_nsf'
    code_rep = Column(Integer, ForeignKey('repertoires.code', ondelete='CASCADE'), primary_key=True)
    code_nsf = Column(String(50), ForeignKey('nsf.code', ondelete='CASCADE'), primary_key=True)

# Table de relation : repertoires_rome
class RepertoiresROME(Base):
    __tablename__ = 'repertoires_rome'
    code_rep = Column(Integer, ForeignKey('repertoires.code', ondelete='CASCADE'), primary_key=True)
    code_rome = Column(String(50), ForeignKey('rome.code', ondelete='CASCADE'), primary_key=True)

# Table de relation : repertoires_forma
class RepertoiresForma(Base):
    __tablename__ = 'repertoires_forma'
    code_rep = Column(Integer, ForeignKey('repertoires.code', ondelete='CASCADE'), primary_key=True)
    code_forma = Column(String(50), ForeignKey('forma.code', ondelete='CASCADE'), primary_key=True)

# Table de relation : certificateurs
class Certificateurs(Base):
    __tablename__ = 'certificateurs'
    code_rep = Column(Integer, ForeignKey('repertoires.code', ondelete='CASCADE'), primary_key=True)
    siret = Column(String(14), ForeignKey('organismes.siret', ondelete='CASCADE'), primary_key=True)

# Table de relation : evaluateurs
class Evaluateurs(Base):
    __tablename__ = 'evaluateurs'
    code_rep = Column(Integer, ForeignKey('repertoires.code', ondelete='CASCADE'), primary_key=True)
    siret = Column(String(14), ForeignKey('organismes.siret', ondelete='CASCADE'), primary_key=True)

# Table de relation : formateurs
class Formateurs(Base):
    __tablename__ = 'formateurs'
    code_rep = Column(Integer, ForeignKey('repertoires.code', ondelete='CASCADE'), primary_key=True)
    siret = Column(String(14), ForeignKey('organismes.siret', ondelete='CASCADE'), primary_key=True)

def create_database(db_path: str):
    """
    Crée la base de données SQLite et les tables.
    Args:
        db_path (str): Chemin vers le fichier SQLite.
    """
    engine = create_engine(f'sqlite:///{db_path}')
    Base.metadata.create_all(engine)
    print(f"Base de données créée avec succès à : {db_path}")

if __name__ == "__main__":
    # Chemin vers le fichier SQLite
    db_path = "/home/tahtoh/RNCP-database/rncp_database.sqlite"
    create_database(db_path)
