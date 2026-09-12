"""
Medicion de concurrencia (RF3-RF8 + nota de medicion del taller).

Uso sugerido: envolver cada etapa (crawling, matching, verificacion,
clasificacion) con medir_tiempo, y guardar el resultado en la tabla
MetricaEjecucion para poder comparar 1 worker vs. N workers bajo las
mismas condiciones (misma persona, mismas fuentes, mismo limite de URLs).
"""
import time
from contextlib import contextmanager

from sqlalchemy.orm import Session

from app import models


@contextmanager
def medir_tiempo():
    """
    Uso:
        with medir_tiempo() as cronometro:
            ... codigo a medir ...
        print(cronometro["segundos"])
    """
    datos = {}
    inicio = time.perf_counter()
    try:
        yield datos
    finally:
        datos["segundos"] = time.perf_counter() - inicio


def registrar_metrica(
    db: Session,
    busqueda_id: str,
    etapa: str,
    num_workers: int,
    tiempo_total_seg: float,
    num_items_procesados: int,
) -> models.MetricaEjecucion:
    metrica = models.MetricaEjecucion(
        busqueda_id=busqueda_id,
        etapa=etapa,
        num_workers=num_workers,
        tiempo_total_seg=tiempo_total_seg,
        num_items_procesados=num_items_procesados,
    )
    db.add(metrica)
    db.commit()
    db.refresh(metrica)
    return metrica
