"""
RF5: Identificacion de contenido relacionado.

Enfoque: scoring por presencia de cada atributo de la persona (RF1) en
el texto. El nombre o un alias es obligatorio para considerar relacion;
los demas atributos suman confianza.
"""
from dataclasses import dataclass
from typing import List, Optional

from app.crawler.fetcher import normalizar
from app.models import Persona

# Umbral minimo de score para considerar el contenido relacionado.
UMBRAL_RELACIONADO = 1.0

PESOS = {
    "nombre": 1.0,
    "alias": 1.0,
    "ciudad": 0.3,
    "profesion": 0.3,
    "empresa": 0.4,
    "palabra_relacionada": 0.2,
}


@dataclass
class ResultadoMatching:
    relacionado: bool
    score: float
    atributos_encontrados: List[str]
    motivo_descarte: Optional[str] = None


def _lista_desde_csv(valor: Optional[str]) -> List[str]:
    if not valor:
        return []
    return [v.strip() for v in valor.split(",") if v.strip()]


def es_contenido_relacionado(texto: str, persona: Persona) -> ResultadoMatching:
    texto_norm = normalizar(texto or "")
    score = 0.0
    encontrados = []

    nombre_norm = normalizar(persona.nombre_completo)
    if nombre_norm and nombre_norm in texto_norm:
        score += PESOS["nombre"]
        encontrados.append(f"nombre:{persona.nombre_completo}")

    for alias in _lista_desde_csv(persona.alias):
        if normalizar(alias) in texto_norm:
            score += PESOS["alias"]
            encontrados.append(f"alias:{alias}")
            break  # un alias es suficiente, no sumar varias veces

    if persona.ciudad and normalizar(persona.ciudad) in texto_norm:
        score += PESOS["ciudad"]
        encontrados.append(f"ciudad:{persona.ciudad}")

    if persona.profesion_cargo and normalizar(persona.profesion_cargo) in texto_norm:
        score += PESOS["profesion"]
        encontrados.append(f"profesion:{persona.profesion_cargo}")

    if persona.empresa_organizacion and normalizar(persona.empresa_organizacion) in texto_norm:
        score += PESOS["empresa"]
        encontrados.append(f"empresa:{persona.empresa_organizacion}")

    for palabra in _lista_desde_csv(persona.palabras_relacionadas):
        if normalizar(palabra) in texto_norm:
            score += PESOS["palabra_relacionada"]
            encontrados.append(f"palabra:{palabra}")

    relacionado = score >= UMBRAL_RELACIONADO

    motivo = None
    if not relacionado:
        if not encontrados:
            motivo = (
                f"No se encontro el nombre '{persona.nombre_completo}' ni ningun alias, "
                "ciudad, profesion, empresa o palabra relacionada en el contenido."
            )
        else:
            motivo = (
                f"Score insuficiente ({score:.2f} < {UMBRAL_RELACIONADO}). "
                f"Solo se encontraron atributos secundarios: {', '.join(encontrados)}."
            )

    return ResultadoMatching(
        relacionado=relacionado,
        score=score,
        atributos_encontrados=encontrados,
        motivo_descarte=motivo,
    )
