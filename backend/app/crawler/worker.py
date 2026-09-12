"""
Logica que ejecuta cada worker/thread del pool (RF3), integrando
RF5 (matching), RF6 (extraccion/persistencia), RF7 (identidad) y
RF8 (clasificacion) por cada URL procesada.
"""
import hashlib

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.analysis.classification import clasificar_documento_con_ia
from app.analysis.identity import verificar_identidad
from app.analysis.matching import es_contenido_relacionado
from app.crawler.fetcher import fetch_url
from app.models import (
    Busqueda, ClasificacionContextual, Descarte, Documento, EstadoUrl,
    Persona, ResultadoIdentidad, UrlEstado, VerificacionIdentidad,
)


def procesar_url(db: Session, gestor, url: str, busqueda: Busqueda, persona: Persona, worker_id: str) -> str:
    """
    Procesa una URL completa: descarga, matching, identidad, clasificacion.
    Devuelve el estado final como string, util para logging/tests.
    """
    url_estado = db.query(UrlEstado).filter_by(busqueda_id=busqueda.id, url=url).first()
    if url_estado is None:
        url_estado = UrlEstado(
            busqueda_id=busqueda.id,
            url=url,
            estado=EstadoUrl.PENDIENTE,
        )
        db.add(url_estado)
        db.commit()
        db.refresh(url_estado)

    url_estado.estado = EstadoUrl.EN_PROCESAMIENTO
    url_estado.worker_id = worker_id
    url_estado.intentos += 1
    db.commit()

    resultado = fetch_url(url)

    if not resultado.ok:
        url_estado.estado = EstadoUrl.ERROR
        db.commit()
        return "ERROR"

    # RF3/RF4: incorporar nuevos enlaces descubiertos a la cola compartida.
    # IMPORTANTE: se reclama la URL, se persiste su fila en la BD y se
    # hace commit ANTES de encolarla (gestor.encolar). Si se encolara
    # primero, otro worker podria tomarla y consultarla en la BD antes
    # de que este commit exista, y ambos intentarian insertar la misma
    # fila (condicion de carrera real, viola la UniqueConstraint de RF4).
    nuevas_filas = []
    for enlace in resultado.enlaces:
        if gestor.reclamar(enlace):
            existe = db.query(UrlEstado).filter_by(busqueda_id=busqueda.id, url=enlace).first()
            if not existe:
                db.add(UrlEstado(
                    busqueda_id=busqueda.id,
                    fuente_id=url_estado.fuente_id,
                    url=enlace,
                    estado=EstadoUrl.PENDIENTE,
                ))
            nuevas_filas.append(enlace)

    if nuevas_filas:
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
        for enlace in nuevas_filas:
            gestor.encolar(enlace)

    # RF5: contenido relacionado
    matching_result = es_contenido_relacionado(resultado.texto or "", persona)
    if not matching_result.relacionado:
        url_estado.estado = EstadoUrl.DESCARTADA
        db.add(Descarte(url_estado_id=url_estado.id, motivo=matching_result.motivo_descarte))
        db.commit()
        return "DESCARTADA"

    # RF6: extraccion y persistencia, evitando duplicados dentro de la busqueda
    hash_contenido = hashlib.sha256((resultado.texto or "").encode("utf-8")).hexdigest()
    ya_existe = (
        db.query(Documento)
        .filter_by(busqueda_id=busqueda.id, hash_contenido=hash_contenido)
        .first()
    )
    if ya_existe:
        url_estado.estado = EstadoUrl.PROCESADA
        db.commit()
        return "PROCESADA (duplicado, no se re-persistio)"

    documento = Documento(
        busqueda_id=busqueda.id,
        url_estado_id=url_estado.id,
        fuente_id=url_estado.fuente_id,
        titulo=resultado.titulo,
        url=url,
        pais=busqueda.pais,
        contenido_texto=resultado.texto,
        hash_contenido=hash_contenido,
        persona_id=persona.id,
    )
    db.add(documento)
    db.flush()  # asigna documento.id sin forzar un commit/fsync todavia

    # RF7: verificacion de identidad
    verificacion = verificar_identidad(resultado.texto or "", persona)
    db.add(VerificacionIdentidad(
        documento_id=documento.id,
        resultado=verificacion.resultado,
        score=verificacion.score,
        evidencia=verificacion.evidencia,
    ))

    # RF8: clasificacion contextual, solo si hay coincidencia de identidad
    if verificacion.resultado in (ResultadoIdentidad.MISMA_PERSONA, ResultadoIdentidad.POSIBLE_COINCIDENCIA):
        clasificacion = clasificar_documento_con_ia(resultado.texto or "", persona.nombre_completo, persona.alias)
        db.add(ClasificacionContextual(
            documento_id=documento.id,
            resultado=clasificacion.resultado,
            score=clasificacion.score,
            justificacion=clasificacion.justificacion,
        ))

    # Un unico commit final para todo lo relacionado con este documento,
    # en vez de varios commits sucesivos (menos contencion de escritura
    # entre workers concurrentes, mismo resultado final).
    url_estado.estado = EstadoUrl.PROCESADA
    db.commit()
    return "PROCESADA"
