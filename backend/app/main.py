"""
Punto de entrada de la API. Ejecutar con:
    uvicorn app.main:app --reload
"""
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import Base, engine
from app.routers import personas, fuentes, busquedas, resultados

# Crea las tablas si no existen (para prototipado rapido).
# En produccion, usar Alembic para migraciones versionadas.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Pepito Plus API",
    description="Plataforma de busqueda y clasificacion de informacion publica sobre una persona.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ajustar en produccion
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(personas.router)
app.include_router(fuentes.router)
app.include_router(busquedas.router)
app.include_router(resultados.router)


@app.get("/")
def raiz():
    return {"status": "ok", "servicio": "Pepito Plus API"}
