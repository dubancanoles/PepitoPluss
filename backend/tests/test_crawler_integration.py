"""
Prueba de integracion de punta a punta: RF3 (crawler concurrente),
RF4 (control de URLs), RF5 (matching), RF6 (persistencia sin duplicados),
RF7 (identidad) y RF8 (clasificacion), todo junto, contra un servidor
HTTP local simulado (no se usa internet real).
"""
import http.server
import socketserver
import threading

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.crawler import queue_manager
from app.db import Base
from app.models import (
    Busqueda, ClasificacionContexto, Documento, EstadoUrl, Fuente,
    Persona, ResultadoIdentidad, TipoFuente, UrlEstado,
)

PAGINA_POSITIVA = """<html><head><title>Reconocimiento</title></head><body>
<p>Pepito Perez Gomez, ingeniero de software de Barranquilla, fue premiado
y reconocido por su trabajo en Pepito Plus SAS.</p>
</body></html>"""

PAGINA_NEGATIVA = """<html><head><title>Investigacion</title></head><body>
<p>Pepito Perez Gomez, de Barranquilla, fue acusado de fraude en un caso
judicial que atrajo la atencion de los medios.</p>
</body></html>"""

PAGINA_NO_RELACIONADA = """<html><head><title>Clima</title></head><body>
<p>El pronostico del tiempo para mañana indica lluvias en la region caribe.</p>
</body></html>"""


def _seed_html(port):
    return f"""<html><body>
    <a href="http://127.0.0.1:{port}/positiva.html">positiva</a>
    <a href="http://127.0.0.1:{port}/negativa.html">negativa</a>
    <a href="http://127.0.0.1:{port}/norelacionada.html">no relacionada</a>
    </body></html>"""


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        rutas = {
            "/seed.html": _seed_html(self.server.server_address[1]),
            "/positiva.html": PAGINA_POSITIVA,
            "/negativa.html": PAGINA_NEGATIVA,
            "/norelacionada.html": PAGINA_NO_RELACIONADA,
        }
        contenido = rutas.get(self.path)
        if contenido is None:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(contenido.encode("utf-8"))

    def log_message(self, format, *args):
        pass  # silenciar logs del servidor de prueba


@pytest.fixture()
def servidor_local():
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", 0), _Handler)
    puerto = httpd.server_address[1]
    hilo = threading.Thread(target=httpd.serve_forever, daemon=True)
    hilo.start()
    yield puerto
    httpd.shutdown()


@pytest.fixture()
def db_temporal(tmp_path, monkeypatch):
    ruta_db = tmp_path / "test_crawler.db"
    engine = create_engine(
        f"sqlite:///{ruta_db}", connect_args={"check_same_thread": False, "timeout": 30}
    )
    Base.metadata.create_all(bind=engine)
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    monkeypatch.setattr(queue_manager, "SessionLocal", TestSessionLocal)
    yield TestSessionLocal


def test_crawling_end_to_end(servidor_local, db_temporal):
    puerto = servidor_local
    SessionLocal = db_temporal

    db = SessionLocal()
    db.add(Persona(
        id="p1", nombre_completo="Pepito Perez Gomez", pais="Colombia",
        ciudad="Barranquilla", empresa_organizacion="Pepito Plus SAS",
    ))
    db.add(Fuente(
        id="f1", nombre="Sitio de prueba",
        url_inicial=f"http://127.0.0.1:{puerto}/seed.html",
        pais="Colombia", tipo=TipoFuente.OTRO, activa=True,
    ))
    db.add(Busqueda(id="b1", persona_id="p1", pais="Colombia", num_workers_usado=4, estado="EN_EJECUCION"))
    db.commit()
    db.close()

    resumen = queue_manager.ejecutar_busqueda("b1", num_workers=4, max_paginas=10)
    assert resumen["urls_procesadas"] >= 3

    db = SessionLocal()

    # RF6: se persistieron exactamente los 2 documentos relacionados, sin duplicados
    documentos = db.query(Documento).filter_by(busqueda_id="b1").all()
    assert len(documentos) == 2
    urls_guardadas = {d.url for d in documentos}
    assert f"http://127.0.0.1:{puerto}/positiva.html" in urls_guardadas
    assert f"http://127.0.0.1:{puerto}/negativa.html" in urls_guardadas

    # RF5: la pagina no relacionada quedo DESCARTADA con motivo, no como Documento
    no_relacionada = db.query(UrlEstado).filter_by(
        busqueda_id="b1", url=f"http://127.0.0.1:{puerto}/norelacionada.html"
    ).first()
    assert no_relacionada.estado == EstadoUrl.DESCARTADA
    assert no_relacionada.descarte is not None
    assert no_relacionada.descarte.motivo

    # RF4: todas las URLs terminaron en un estado valido, ninguna quedo colgada
    estados_finales = {u.estado for u in db.query(UrlEstado).filter_by(busqueda_id="b1").all()}
    assert estados_finales.issubset({EstadoUrl.PROCESADA, EstadoUrl.DESCARTADA, EstadoUrl.ERROR})

    # RF7: cada documento relacionado tiene verificacion de identidad
    for doc in documentos:
        assert doc.verificacion is not None
        assert doc.verificacion.resultado in (
            ResultadoIdentidad.MISMA_PERSONA, ResultadoIdentidad.POSIBLE_COINCIDENCIA,
        )

    # RF8: el documento positivo y el negativo se clasifican distinto (por contexto real)
    doc_positivo = next(d for d in documentos if "positiva" in d.url)
    doc_negativo = next(d for d in documentos if "negativa" in d.url)
    assert doc_positivo.clasificacion.resultado == ClasificacionContexto.POSITIVO
    assert doc_negativo.clasificacion.resultado == ClasificacionContexto.NEGATIVO

    db.close()


def test_crawling_evita_reprocesar_si_se_corre_dos_veces(servidor_local, db_temporal):
    """RF6: correr la extraccion sobre el mismo contenido no debe duplicar documentos."""
    puerto = servidor_local
    SessionLocal = db_temporal

    db = SessionLocal()
    db.add(Persona(id="p1", nombre_completo="Pepito Perez Gomez", pais="Colombia", ciudad="Barranquilla"))
    db.add(Fuente(
        id="f1", nombre="Sitio de prueba",
        url_inicial=f"http://127.0.0.1:{puerto}/positiva.html",
        pais="Colombia", tipo=TipoFuente.OTRO, activa=True,
    ))
    db.add(Busqueda(id="b1", persona_id="p1", pais="Colombia", num_workers_usado=2, estado="EN_EJECUCION"))
    db.commit()
    db.close()

    queue_manager.ejecutar_busqueda("b1", num_workers=2, max_paginas=5)

    db = SessionLocal()
    documentos = db.query(Documento).filter_by(busqueda_id="b1").all()
    assert len(documentos) == 1  # una sola pagina real, sin duplicados
    db.close()
