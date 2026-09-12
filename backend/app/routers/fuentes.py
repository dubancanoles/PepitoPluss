"""
RF2: Administracion de fuentes por pais.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db import get_db
from app import models, schemas

router = APIRouter(prefix="/fuentes", tags=["fuentes"])


@router.post("", response_model=schemas.FuenteOut, status_code=201)
def crear_fuente(payload: schemas.FuenteCreate, db: Session = Depends(get_db)):
    fuente = models.Fuente(**payload.model_dump())
    db.add(fuente)
    db.commit()
    db.refresh(fuente)
    return fuente


@router.get("", response_model=List[schemas.FuenteOut])
def listar_fuentes(
    pais: Optional[str] = None,
    activa: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    query = db.query(models.Fuente)
    if pais:
        query = query.filter(func.lower(models.Fuente.pais) == pais.strip().lower())
    if activa is not None:
        query = query.filter(models.Fuente.activa == activa)
    return query.all()


@router.patch("/{fuente_id}/estado", response_model=schemas.FuenteOut)
def cambiar_estado_fuente(fuente_id: str, activa: bool, db: Session = Depends(get_db)):
    fuente = db.query(models.Fuente).get(fuente_id)
    if not fuente:
        raise HTTPException(404, "Fuente no encontrada")
    fuente.activa = activa
    db.commit()
    db.refresh(fuente)
    return fuente
