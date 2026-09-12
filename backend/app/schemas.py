"""
Esquemas Pydantic (contratos de entrada/salida de la API).
"""
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, ConfigDict

from app.models import TipoFuente, EstadoUrl, ResultadoIdentidad, ClasificacionContexto


# ---------------------------------------------------------------------------
# Persona (RF1)
# ---------------------------------------------------------------------------

class PersonaCreate(BaseModel):
    nombre_completo: str  # obligatorio
    pais: str             # obligatorio
    ciudad: Optional[str] = None
    profesion_cargo: Optional[str] = None
    empresa_organizacion: Optional[str] = None
    alias: Optional[str] = None
    palabras_relacionadas: Optional[str] = None


class PersonaOut(PersonaCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    creado_en: datetime


# ---------------------------------------------------------------------------
# Fuente (RF2)
# ---------------------------------------------------------------------------

class FuenteCreate(BaseModel):
    nombre: str
    url_inicial: str
    pais: str
    tipo: TipoFuente = TipoFuente.OTRO
    activa: bool = True


class FuenteOut(FuenteCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    creado_en: datetime


# ---------------------------------------------------------------------------
# Busqueda
# ---------------------------------------------------------------------------

class BusquedaCreate(BaseModel):
    persona_id: str
    pais: str
    num_workers: int = 4


class BusquedaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    persona_id: str
    pais: str
    fecha_inicio: datetime
    fecha_fin: Optional[datetime] = None
    num_workers_usado: int
    estado: str


# ---------------------------------------------------------------------------
# Resultados (RF9)
# ---------------------------------------------------------------------------

class DocumentoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    titulo: Optional[str] = None
    url: str
    fuente_id: Optional[str] = None
    fuente_nombre: Optional[str] = None
    pais: Optional[str] = None
    fecha_publicacion: Optional[datetime] = None
    fecha_consulta: datetime
    contenido_texto: Optional[str] = None
    estado_identidad: Optional[ResultadoIdentidad] = None
    clasificacion: Optional[ClasificacionContexto] = None


class DescarteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    url: str
    motivo: str
