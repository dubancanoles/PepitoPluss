"""
RF9: Consulta y filtrado de resultados.
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app import models, schemas

router = APIRouter(prefix="/resultados", tags=["resultados"])


@router.get("/{busqueda_id}/documentos", response_model=List[schemas.DocumentoOut])
def listar_documentos(
    busqueda_id: str,
    clasificacion: Optional[str] = None,   # POSITIVO / NEUTRO / NEGATIVO / NO_DETERMINADO
    fuente_id: Optional[str] = None,
    fecha_desde: Optional[datetime] = None,
    fecha_hasta: Optional[datetime] = None,
    estado_identidad: Optional[str] = None,  # MISMA_PERSONA / POSIBLE_COINCIDENCIA / ...
    db: Session = Depends(get_db),
):
    query = db.query(models.Documento).filter(models.Documento.busqueda_id == busqueda_id)

    if fuente_id:
        query = query.filter(models.Documento.fuente_id == fuente_id)
    if fecha_desde:
        query = query.filter(models.Documento.fecha_publicacion >= fecha_desde)
    if fecha_hasta:
        query = query.filter(models.Documento.fecha_publicacion <= fecha_hasta)

    if clasificacion:
        query = query.join(models.ClasificacionContextual).filter(
            models.ClasificacionContextual.resultado == clasificacion
        )
    if estado_identidad:
        query = query.join(models.VerificacionIdentidad).filter(
            models.VerificacionIdentidad.resultado == estado_identidad
        )

    documentos = query.all()
    return [
        schemas.DocumentoOut(
            id=documento.id,
            titulo=documento.titulo,
            url=documento.url,
            fuente_id=documento.fuente_id,
            fuente_nombre=(
                db.query(models.Fuente.nombre)
                .filter(models.Fuente.id == documento.fuente_id)
                .scalar()
                if documento.fuente_id else None
            ),
            pais=documento.pais,
            fecha_publicacion=documento.fecha_publicacion,
            fecha_consulta=documento.fecha_consulta,
            contenido_texto=documento.contenido_texto,
            estado_identidad=(documento.verificacion.resultado if documento.verificacion else None),
            clasificacion=(documento.clasificacion.resultado if documento.clasificacion else None),
        )
        for documento in documentos
    ]


@router.get("/{busqueda_id}/descartados", response_model=List[schemas.DescarteOut])
def listar_descartados(busqueda_id: str, db: Session = Depends(get_db)):
    """RF5: permite consultar los elementos descartados y el motivo."""
    resultados = (
        db.query(models.UrlEstado, models.Descarte)
        .join(models.Descarte, models.Descarte.url_estado_id == models.UrlEstado.id)
        .filter(models.UrlEstado.busqueda_id == busqueda_id)
        .all()
    )
    return [
        schemas.DescarteOut(url=url_estado.url, motivo=descarte.motivo)
        for url_estado, descarte in resultados
    ]
