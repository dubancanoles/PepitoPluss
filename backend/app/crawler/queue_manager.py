"""
RF3: Crawling concurrente.
RF4: Control concurrente de URLs (estados + evitar doble procesamiento).
"""
import queue
import multiprocessing
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from math import ceil
from urllib.parse import urlparse

from app.crawler.worker import procesar_url
from app.db import SessionLocal
from sqlalchemy import func
from app.metrics import registrar_metrica
from app.models import Busqueda, EstadoUrl, Fuente, Persona, UrlEstado


class GestorColaURLs:
    """
    Envuelve una queue.Queue + un dict de 'vistas' protegido con Lock,
    para garantizar que ninguna URL se encole ni se procese dos veces
    dentro de una misma busqueda, incluso si varios workers la descubren
    casi al mismo tiempo desde paginas distintas.
    Ajustado para multiprocesamiento usando multiprocessing.Manager.
    """

    def __init__(self, cola, vistas, contadas_por_dominio, lock, max_urls_por_dominio=None):
        self._cola = cola
        self._vistas = vistas
        self._contadas_por_dominio = contadas_por_dominio
        self._max_urls_por_dominio = max_urls_por_dominio
        self._lock = lock

    def reclamar(self, url: str) -> bool:
        """
        Marca la URL como 'vista' SIN encolarla todavia. Devuelve True
        solo para la primera llamada que reclama esa URL.

        Se separa de `encolar` a proposito: si el llamador necesita
        persistir la fila de la URL en la base de datos, debe hacerlo
        DESPUES de reclamar() y ANTES de encolar(). De lo contrario hay
        una condicion de carrera real: otro worker podria sacar la URL
        de la cola y buscarla en la BD antes de que el commit del primer
        worker se haya ejecutado, y ambos terminarian intentando
        insertar la misma fila (viola la UniqueConstraint de RF4).
        """
        with self._lock:
            if url in self._vistas:
                return False
            dominio = (urlparse(url).hostname or "").lower()
            contadas = self._contadas_por_dominio.get(dominio, 0)
            if self._max_urls_por_dominio and contadas >= self._max_urls_por_dominio:
                return False
            self._vistas[url] = True
            self._contadas_por_dominio[dominio] = contadas + 1
            return True

    def encolar(self, url: str) -> None:
        self._cola.put(url)

    def encolar_si_nueva(self, url: str) -> bool:
        """Atajo: reclamar + encolar en un solo paso. Usar solo cuando no
        hay nada que persistir en la BD antes de que la URL sea visible
        para otros workers (p.ej. la siembra inicial, antes de lanzar
        el pool de threads)."""
        if self.reclamar(url):
            self.encolar(url)
            return True
        return False

    def obtener(self, timeout: float = 1.0):
        try:
            return self._cola.get(timeout=timeout)
        except queue.Empty:
            return None

    def esta_vacia(self) -> bool:
        return self._cola.empty()


def _worker_loop(gestor: GestorColaURLs, contador, lock_contador,
                  max_paginas: int, busqueda_id: str, worker_id: str):
    """Bucle que corre en cada proceso del pool hasta que no haya trabajo o se
    alcance el limite de exploracion configurado."""
    db = SessionLocal()
    try:
        busqueda = db.query(Busqueda).get(busqueda_id)
        persona = db.query(Persona).get(busqueda.persona_id)

        while True:
            with lock_contador:
                if contador["procesadas"] >= max_paginas:
                    break

            url = gestor.obtener(timeout=0.5)
            if url is None:
                # La cola puede quedar vacia mientras otro worker descarga
                # una pagina y todavia no ha descubierto sus enlaces.
                with lock_contador:
                    no_hay_trabajo = (
                        gestor.esta_vacia() and contador["en_proceso"] == 0
                    )
                if no_hay_trabajo:
                    break
                continue

            with lock_contador:
                contador["en_proceso"] += 1
            try:
                procesar_url(db, gestor, url, busqueda, persona, worker_id)
            finally:
                with lock_contador:
                    contador["en_proceso"] -= 1
                    contador["procesadas"] += 1
    finally:
        db.close()


def ejecutar_busqueda(busqueda_id: str, num_workers: int, max_paginas: int = 1000) -> dict:
    """
    Punto de entrada de RF3. Arma la cola con las URLs semilla de las
    fuentes activas del pais de la busqueda, lanza un pool de procesos
    (ProcessPoolExecutor) y espera a que terminen.

    Devuelve un resumen con tiempos y conteos, y ademas queda registrado
    en la tabla MetricaEjecucion (para la comparacion 1 vs N workers).
    """
    db = SessionLocal()
    try:
        busqueda = db.query(Busqueda).get(busqueda_id)
        if busqueda is None:
            raise ValueError(f"Busqueda {busqueda_id} no existe")

        fuentes_activas = (
            db.query(Fuente)
            .filter(func.lower(Fuente.pais) == busqueda.pais.strip().lower(), Fuente.activa.is_(True))
            .all()
        )

        dominios = {
            (urlparse(fuente.url_inicial).hostname or "").lower()
            for fuente in fuentes_activas
        }
        limite_por_dominio = max(1, ceil(max_paginas / max(len(dominios), 1)))
        
        manager = multiprocessing.Manager()
        gestor = GestorColaURLs(
            cola=manager.Queue(),
            vistas=manager.dict(),
            contadas_por_dominio=manager.dict(),
            lock=manager.Lock(),
            max_urls_por_dominio=limite_por_dominio
        )

        # Sembrar la cola con las URLs iniciales de cada fuente activa
        for fuente in fuentes_activas:
            if gestor.encolar_si_nueva(fuente.url_inicial):
                existe = db.query(UrlEstado).filter_by(
                    busqueda_id=busqueda.id, url=fuente.url_inicial
                ).first()
                if not existe:
                    db.add(UrlEstado(
                        busqueda_id=busqueda.id,
                        fuente_id=fuente.id,
                        url=fuente.url_inicial,
                        estado=EstadoUrl.PENDIENTE,
                    ))
        db.commit()
    finally:
        db.close()

    contador = manager.dict({"procesadas": 0, "en_proceso": 0})
    lock_contador = manager.Lock()

    inicio = time.perf_counter()
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        futuros = [
            executor.submit(
                _worker_loop, gestor, contador, lock_contador,
                max_paginas, busqueda_id, f"worker-{i+1}"
            )
            for i in range(num_workers)
        ]
        for f in futuros:
            f.result()  # propaga excepciones si algun worker fallo
    tiempo_total = time.perf_counter() - inicio

    db = SessionLocal()
    try:
        busqueda = db.query(Busqueda).get(busqueda_id)
        busqueda.estado = "FINALIZADA"
        busqueda.fecha_fin = datetime.utcnow()
        db.commit()

        registrar_metrica(
            db, busqueda_id=busqueda_id, etapa="crawling",
            num_workers=num_workers, tiempo_total_seg=tiempo_total,
            num_items_procesados=contador["procesadas"],
        )
    finally:
        db.close()

    return {"tiempo_total_seg": tiempo_total, "urls_procesadas": contador["procesadas"]}
