"""
Modelo de datos principal de Pepito Plus.
Aquí definimos las tablas de la base de datos usando SQLAlchemy.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, ForeignKey, Text,
    Enum as SAEnum, Float, UniqueConstraint
)
from sqlalchemy.orm import relationship

from app.db import Base


def gen_uuid() -> str:
    # Genera un ID único para las llaves primarias
    return str(uuid.uuid4())


class EstadoUrl(str, enum.Enum):
    # Diferentes fases por las que pasa una URL al ser descubierta por el crawler
    PENDIENTE = "PENDIENTE"
    EN_PROCESAMIENTO = "EN_PROCESAMIENTO"
    PROCESADA = "PROCESADA"
    DESCARTADA = "DESCARTADA"
    ERROR = "ERROR"


class ResultadoIdentidad(str, enum.Enum):
    # Niveles de certeza al comparar la persona encontrada con la que buscamos
    MISMA_PERSONA = "MISMA_PERSONA"
    POSIBLE_COINCIDENCIA = "POSIBLE_COINCIDENCIA"
    PERSONA_DIFERENTE = "PERSONA_DIFERENTE"
    NO_DETERMINADO = "NO_DETERMINADO"


class ClasificacionContexto(str, enum.Enum):
    # Categorías para saber de qué trata el artículo (si habla bien, mal, o es neutral)
    POSITIVO = "POSITIVO"
    NEUTRO = "NEUTRO"
    NEGATIVO = "NEGATIVO"
    NO_DETERMINADO = "NO_DETERMINADO"


class TipoFuente(str, enum.Enum):
    NOTICIAS = "NOTICIAS"
    RED_SOCIAL = "RED_SOCIAL"
    BLOG = "BLOG"
    DIRECTORIO_PUBLICO = "DIRECTORIO_PUBLICO"
    OTRO = "OTRO"


class Persona(Base):
    # Almacena los datos del sujeto que estamos investigando
    __tablename__ = "personas"

    id = Column(String, primary_key=True, default=gen_uuid)
    nombre_completo = Column(String, nullable=False, index=True)
    pais = Column(String, nullable=False, index=True)
    ciudad = Column(String, nullable=True)
    profesion_cargo = Column(String, nullable=True)
    empresa_organizacion = Column(String, nullable=True)
    alias = Column(String, nullable=True)  # Guardamos los apodos separados por comas
    palabras_relacionadas = Column(String, nullable=True)
    creado_en = Column(DateTime, default=datetime.utcnow)

    busquedas = relationship("Busqueda", back_populates="persona")


class Fuente(Base):
    # Sitios web semilla desde donde arranca a buscar el crawler
    __tablename__ = "fuentes"

    id = Column(String, primary_key=True, default=gen_uuid)
    nombre = Column(String, nullable=False)
    url_inicial = Column(String, nullable=False)
    pais = Column(String, nullable=False, index=True)  # Se refiere al alcance del portal web, no dónde está el servidor
    tipo = Column(SAEnum(TipoFuente), nullable=False, default=TipoFuente.OTRO)
    activa = Column(Boolean, default=True)
    creado_en = Column(DateTime, default=datetime.utcnow)


class Busqueda(Base):
    # Historial de cada vez que el usuario hace clic en "Buscar"
    __tablename__ = "busquedas"

    id = Column(String, primary_key=True, default=gen_uuid)
    persona_id = Column(String, ForeignKey("personas.id"), nullable=False)
    pais = Column(String, nullable=False)
    fecha_inicio = Column(DateTime, default=datetime.utcnow)
    fecha_fin = Column(DateTime, nullable=True)
    num_workers_usado = Column(Integer, default=1)
    estado = Column(String, default="EN_EJECUCION")  # EN_EJECUCION, FINALIZADA o ERROR

    persona = relationship("Persona", back_populates="busquedas")
    urls = relationship("UrlEstado", back_populates="busqueda")
    documentos = relationship("Documento", back_populates="busqueda")
    metricas = relationship("MetricaEjecucion", back_populates="busqueda")


class UrlEstado(Base):
    # Controla qué páginas ya visitamos para no repetir el trabajo en múltiples procesos
    __tablename__ = "url_estados"
    __table_args__ = (
        UniqueConstraint("busqueda_id", "url", name="uq_busqueda_url"),
    )

    id = Column(String, primary_key=True, default=gen_uuid)
    busqueda_id = Column(String, ForeignKey("busquedas.id"), nullable=False)
    fuente_id = Column(String, ForeignKey("fuentes.id"), nullable=True)
    url = Column(String, nullable=False, index=True)
    estado = Column(SAEnum(EstadoUrl), default=EstadoUrl.PENDIENTE, nullable=False)
    worker_id = Column(String, nullable=True)  # Guardamos el id del worker para saber quién hizo el trabajo
    intentos = Column(Integer, default=0)
    descubierta_en = Column(DateTime, default=datetime.utcnow)
    actualizada_en = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    busqueda = relationship("Busqueda", back_populates="urls")
    descarte = relationship("Descarte", back_populates="url_estado", uselist=False)


class Descarte(Base):
    # Si una página no sirve, guardamos aquí la razón para tener un registro de por qué se descartó
    __tablename__ = "descartes"

    id = Column(String, primary_key=True, default=gen_uuid)
    url_estado_id = Column(String, ForeignKey("url_estados.id"), nullable=False, unique=True)
    motivo = Column(Text, nullable=False)
    creado_en = Column(DateTime, default=datetime.utcnow)

    url_estado = relationship("UrlEstado", back_populates="descarte")


class Documento(Base):
    # Guarda el texto limpio de la noticia o página que sí hablaba de nuestra persona
    __tablename__ = "documentos"
    __table_args__ = (
        UniqueConstraint("busqueda_id", "hash_contenido", name="uq_busqueda_hash"),
    )

    id = Column(String, primary_key=True, default=gen_uuid)
    busqueda_id = Column(String, ForeignKey("busquedas.id"), nullable=False)
    url_estado_id = Column(String, ForeignKey("url_estados.id"), nullable=False)
    fuente_id = Column(String, ForeignKey("fuentes.id"), nullable=True)

    titulo = Column(String, nullable=True)
    url = Column(String, nullable=False)
    pais = Column(String, nullable=True)
    fecha_publicacion = Column(DateTime, nullable=True)
    fecha_consulta = Column(DateTime, default=datetime.utcnow)
    contenido_texto = Column(Text, nullable=True)
    hash_contenido = Column(String, nullable=False, index=True)  # Hash SHA-256 para evitar duplicados si dos diarios publican lo mismo

    persona_id = Column(String, ForeignKey("personas.id"), nullable=False)

    busqueda = relationship("Busqueda", back_populates="documentos")
    verificacion = relationship("VerificacionIdentidad", back_populates="documento", uselist=False)
    clasificacion = relationship("ClasificacionContextual", back_populates="documento", uselist=False)


class VerificacionIdentidad(Base):
    # Resultado del modelo de IA confirmando si es o no el sujeto buscado
    __tablename__ = "verificaciones_identidad"

    id = Column(String, primary_key=True, default=gen_uuid)
    documento_id = Column(String, ForeignKey("documentos.id"), nullable=False, unique=True)
    resultado = Column(SAEnum(ResultadoIdentidad), nullable=False)
    score = Column(Float, nullable=True)
    evidencia = Column(Text, nullable=True)
    creado_en = Column(DateTime, default=datetime.utcnow)

    documento = relationship("Documento", back_populates="verificacion")


class ClasificacionContextual(Base):
    # Resultado del análisis de sentimiento de la noticia
    __tablename__ = "clasificaciones_contextuales"

    id = Column(String, primary_key=True, default=gen_uuid)
    documento_id = Column(String, ForeignKey("documentos.id"), nullable=False, unique=True)
    resultado = Column(SAEnum(ClasificacionContexto), nullable=False)
    score = Column(Float, nullable=True)
    justificacion = Column(Text, nullable=True)
    creado_en = Column(DateTime, default=datetime.utcnow)

    documento = relationship("Documento", back_populates="clasificacion")


class MetricaEjecucion(Base):
    # Usamos esta tabla para medir cuánto tiempo tarda el crawler y comparar el rendimiento
    __tablename__ = "metricas_ejecucion"

    id = Column(String, primary_key=True, default=gen_uuid)
    busqueda_id = Column(String, ForeignKey("busquedas.id"), nullable=False)
    etapa = Column(String, nullable=False)
    num_workers = Column(Integer, nullable=False)
    tiempo_total_seg = Column(Float, nullable=False)
    num_items_procesados = Column(Integer, nullable=False)
    creado_en = Column(DateTime, default=datetime.utcnow)

    busqueda = relationship("Busqueda", back_populates="metricas")
