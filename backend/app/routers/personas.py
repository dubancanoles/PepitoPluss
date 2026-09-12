"""
RF1: Registro de persona a consultar.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app import models, schemas

router = APIRouter(prefix="/personas", tags=["personas"])


@router.post("", response_model=schemas.PersonaOut, status_code=201)
def crear_persona(payload: schemas.PersonaCreate, db: Session = Depends(get_db)):
    if not payload.nombre_completo.strip() or not payload.pais.strip():
        raise HTTPException(400, "nombre_completo y pais son obligatorios")

    persona = models.Persona(**payload.model_dump())
    db.add(persona)
    db.commit()
    db.refresh(persona)
    return persona


@router.get("", response_model=List[schemas.PersonaOut])
def listar_personas(db: Session = Depends(get_db)):
    return db.query(models.Persona).order_by(models.Persona.creado_en.desc()).all()


@router.get("/{persona_id}", response_model=schemas.PersonaOut)
def obtener_persona(persona_id: str, db: Session = Depends(get_db)):
    persona = db.query(models.Persona).get(persona_id)
    if not persona:
        raise HTTPException(404, "Persona no encontrada")
    return persona
