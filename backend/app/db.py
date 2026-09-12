"""
Configuracion de la base de datos.
Por defecto usa SQLite para desarrollo rapido.
Para produccion, define la variable de entorno DATABASE_URL, por ejemplo:
    postgresql://usuario:password@localhost:5432/pepito_plus
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./pepito.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency de FastAPI: entrega una sesion de BD por request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
