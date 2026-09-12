"""
RF7: Verificacion de identidad.

Reglas (heuristica, documentada para la sustentacion):
- Nombre encontrado + >=2 atributos secundarios (ciudad/profesion/empresa/
  palabra relacionada) coincidiendo -> MISMA_PERSONA (alta confianza).
- Nombre encontrado + 1 atributo secundario -> POSIBLE_COINCIDENCIA.
- Nombre encontrado + 0 atributos secundarios, y el texto contiene
  senales explicitas de homonimia ("tocayo", "homonimo", "otro <nombre>",
  "no es el mismo") -> PERSONA_DIFERENTE.
- Nombre encontrado + 0 atributos secundarios, sin senales de homonimia
  -> NO_DETERMINADO (no hay suficiente evidencia para decidir).
- Solo alias (sin nombre completo) + >=1 atributo secundario -> POSIBLE_COINCIDENCIA.
- Cualquier otro caso -> NO_DETERMINADO.
"""
import re
from dataclasses import dataclass
from typing import Optional

from app.analysis.matching import es_contenido_relacionado
from app.crawler.fetcher import normalizar
from app.models import Persona, ResultadoIdentidad

SENALES_HOMONIMIA = [
    "tocayo", "homonimo", "homónimo", "no es el mismo", "otro ",
    "distinta persona", "diferente persona",
]


@dataclass
class ResultadoVerificacion:
    resultado: ResultadoIdentidad
    score: float
    evidencia: Optional[str] = None


def _contiene_senal_homonimia(texto_norm: str) -> bool:
    return any(senal in texto_norm for senal in SENALES_HOMONIMIA)


def verificar_identidad(texto: str, persona: Persona) -> ResultadoVerificacion:
    matching = es_contenido_relacionado(texto, persona)
    texto_norm = normalizar(texto or "")

    tiene_nombre = any(a.startswith("nombre:") for a in matching.atributos_encontrados)
    tiene_alias = any(a.startswith("alias:") for a in matching.atributos_encontrados)
    secundarios = [
        a for a in matching.atributos_encontrados
        if not a.startswith("nombre:") and not a.startswith("alias:")
    ]

    if tiene_nombre and len(secundarios) >= 2:
        return ResultadoVerificacion(
            resultado=ResultadoIdentidad.MISMA_PERSONA,
            score=matching.score,
            evidencia=f"Nombre + {len(secundarios)} atributos secundarios: {secundarios}",
        )

    if tiene_nombre and len(secundarios) == 1:
        return ResultadoVerificacion(
            resultado=ResultadoIdentidad.POSIBLE_COINCIDENCIA,
            score=matching.score,
            evidencia=f"Nombre + 1 atributo secundario: {secundarios}",
        )

    if tiene_nombre and len(secundarios) == 0:
        if _contiene_senal_homonimia(texto_norm):
            return ResultadoVerificacion(
                resultado=ResultadoIdentidad.PERSONA_DIFERENTE,
                score=matching.score,
                evidencia="Nombre encontrado pero el texto senala explicitamente homonimia.",
            )
        return ResultadoVerificacion(
            resultado=ResultadoIdentidad.NO_DETERMINADO,
            score=matching.score,
            evidencia="Solo se encontro el nombre, sin atributos secundarios ni contradiccion.",
        )

    if tiene_alias and len(secundarios) >= 1:
        return ResultadoVerificacion(
            resultado=ResultadoIdentidad.POSIBLE_COINCIDENCIA,
            score=matching.score,
            evidencia=f"Alias + atributos secundarios: {secundarios}",
        )

    return ResultadoVerificacion(
        resultado=ResultadoIdentidad.NO_DETERMINADO,
        score=matching.score,
        evidencia="Evidencia insuficiente para determinar identidad.",
    )
