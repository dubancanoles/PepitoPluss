"""
Prueba que compara tiempos de ejecucion con 1 worker vs N workers, bajo
las mismas condiciones (mismo servidor, mismas paginas, mismo delay
artificial por pagina) -- esto es exactamente lo que pide la nota de
"Medicion de concurrencia" de la rubrica.

Usamos un servidor HTTP local con un pequeño delay artificial en cada
respuesta para simular latencia de red real; sin el delay, las
diferencias de tiempo serian demasiado pequeñas y ruidosas para medir
de forma confiable en un test.
"""
import http.server
import socketserver
import threading
import time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.crawler import queue_manager
from app.db import Base
from app.models import Busqueda, Fuente, Persona, TipoFuente

DELAY_SEGUNDOS = 0.2
NUM_PAGINAS = 8


def _pagina_html(i):
    enlaces = ""
    return f"<html><head><title>Pagina {i}</title></head><body><p>Contenido generico numero {i}.</p></body></html>"


def _seed_html(port, n):
    enlaces = "".join(f'<a href="http://127.0.0.1:{port}/pagina{i}.html">p{i}</a>' for i in range(n))
    return f"<html><body>{enlaces}</body></html>"


class _HandlerConDelay(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        time.sleep(DELAY_SEGUNDOS)  # simula latencia de red
        if self.path == "/seed.html":
            contenido = _seed_html(self.server.server_address[1], NUM_PAGINAS)
        elif self.path.startswith("/pagina"):
            i = self.path.replace("/pagina", "").replace(".html", "")
            contenido = _pagina_html(i)
        else:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(contenido.encode("utf-8"))

    def log_message(self, format, *args):
        pass


@pytest.fixture()
def servidor_lento():
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", 0), _HandlerConDelay)
    puerto = httpd.server_address[1]
    hilo = threading.Thread(target=httpd.serve_forever, daemon=True)
    hilo.start()
    yield puerto
    httpd.shutdown()


def _preparar_busqueda(SessionLocal, busqueda_id, puerto):
    db = SessionLocal()
    db.add(Persona(id=f"p-{busqueda_id}", nombre_completo="Persona Generica", pais="Colombia"))
    db.add(Fuente(
        id=f"f-{busqueda_id}", nombre="Sitio lento",
        url_inicial=f"http://127.0.0.1:{puerto}/seed.html",
        pais="Colombia", tipo=TipoFuente.OTRO, activa=True,
    ))
    db.add(Busqueda(id=busqueda_id, persona_id=f"p-{busqueda_id}", pais="Colombia", estado="EN_EJECUCION"))
    db.commit()
    db.close()


def test_n_workers_es_mas_rapido_que_1_worker(servidor_lento, tmp_path, monkeypatch):
    puerto = servidor_lento
    ruta_db = tmp_path / "medicion.db"
    engine = create_engine(f"sqlite:///{ruta_db}", connect_args={"check_same_thread": False, "timeout": 30})
    Base.metadata.create_all(bind=engine)
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    monkeypatch.setattr(queue_manager, "SessionLocal", TestSessionLocal)

    # Misma cantidad de paginas, mismo delay por pagina, unica diferencia: num_workers
    _preparar_busqueda(TestSessionLocal, "busq-1worker", puerto)
    resumen_1 = queue_manager.ejecutar_busqueda("busq-1worker", num_workers=1, max_paginas=NUM_PAGINAS + 1)

    _preparar_busqueda(TestSessionLocal, "busq-8workers", puerto)
    resumen_8 = queue_manager.ejecutar_busqueda("busq-8workers", num_workers=8, max_paginas=NUM_PAGINAS + 1)

    print(f"\n1 worker:  {resumen_1['tiempo_total_seg']:.2f}s ({resumen_1['urls_procesadas']} paginas)")
    print(f"8 workers: {resumen_8['tiempo_total_seg']:.2f}s ({resumen_8['urls_procesadas']} paginas)")

    # Con 8 workers debe ser mas rapido que con 1. No esperamos un speedup
    # cercano a 8x: SQLite serializa escrituras (un solo archivo, un writer
    # a la vez) y el parseo HTML con lxml es CPU-bound (compite por el GIL),
    # asi que el cuello de botella deja de ser solo la espera de red. Aun
    # asi, la mejora debe ser real y medible -- eso es lo que se reporta
    # y se explica en la sustentacion (con PostgreSQL en vez de SQLite,
    # el speedup por escritura concurrente séria mayor).
    assert resumen_8["tiempo_total_seg"] < resumen_1["tiempo_total_seg"] * 0.85
