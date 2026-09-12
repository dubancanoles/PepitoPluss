"""
Dispara y consulta el estado de una busqueda.

RF3-RF8 se ejecutan a partir de POST /busquedas.
Por ahora este router deja la busqueda creada en la BD; la logica de
crawling concurrente se conecta aqui en app/crawler/queue_manager.py
(ver TODOs marcados abajo). Implementar en el Dia 2 del plan.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db import get_db
from app import models, schemas
from app.crawler.queue_manager import ejecutar_busqueda

router = APIRouter(prefix="/busquedas", tags=["busquedas"])


@router.post("", response_model=schemas.BusquedaOut, status_code=201)
def iniciar_busqueda(
    payload: schemas.BusquedaCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    persona = db.query(models.Persona).get(payload.persona_id)
    if not persona:
        raise HTTPException(404, "Persona no encontrada")

    fuentes_activas = (
        db.query(models.Fuente)
        .filter(func.lower(models.Fuente.pais) == payload.pais.strip().lower(), models.Fuente.activa.is_(True))
        .count()
    )
    if fuentes_activas == 0:
        raise HTTPException(400, f"No hay fuentes activas para el pais {payload.pais}")

    busqueda = models.Busqueda(
        persona_id=payload.persona_id,
        pais=payload.pais,
        num_workers_usado=payload.num_workers,
        estado="EN_EJECUCION",
    )
    db.add(busqueda)
    db.commit()
    db.refresh(busqueda)

    background_tasks.add_task(ejecutar_busqueda, busqueda.id, payload.num_workers)

    return busqueda


@router.post("/{busqueda_id}/ejecutar-sincrono")
def ejecutar_busqueda_sincrona(busqueda_id: str, num_workers: int = 4, max_paginas: int = 200):
    """
    Variante SINCRONA (espera a que termine antes de responder). Util para
    la demo/sustentacion y para medir tiempos 1 vs N workers de forma
    controlada, sin depender del polling de una tarea en background.
    """
    resumen = ejecutar_busqueda(busqueda_id, num_workers, max_paginas)
    return resumen


@router.get("/{busqueda_id}", response_model=schemas.BusquedaOut)
def obtener_busqueda(busqueda_id: str, db: Session = Depends(get_db)):
    busqueda = db.query(models.Busqueda).get(busqueda_id)
    if not busqueda:
        raise HTTPException(404, "Busqueda no encontrada")
    return busqueda


@router.get("", response_model=List[schemas.BusquedaOut])
def listar_busquedas(db: Session = Depends(get_db)):
    return db.query(models.Busqueda).order_by(models.Busqueda.fecha_inicio.desc()).all()
