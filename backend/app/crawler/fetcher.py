"""
Descarga y parseo de paginas web (RF3).
"""
import re
import unicodedata
from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import parse_qs, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PepitoPlusBot/1.0; taller academico)"
}

MAX_ENLACES_POR_PAGINA = 40
DOMINIOS_EXCLUIDOS = {
    "facebook.com", "m.facebook.com", "twitter.com", "x.com",
    "linkedin.com", "pinterest.com", "whatsapp.com", "api.whatsapp.com",
    "doubleclick.net", "googleadservices.com",
}

META_FECHA_TAGS = [
    ("meta", {"property": "article:published_time"}),
    ("meta", {"name": "date"}),
    ("meta", {"name": "pubdate"}),
    ("meta", {"property": "og:updated_time"}),
]


@dataclass
class ResultadoFetch:
    ok: bool
    status_code: Optional[int]
    titulo: Optional[str] = None
    texto: Optional[str] = None
    fecha_publicacion: Optional[str] = None
    enlaces: List[str] = field(default_factory=list)
    error: Optional[str] = None


def fetch_url(url: str, timeout: int = 10) -> ResultadoFetch:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
    except requests.RequestException as exc:
        return ResultadoFetch(ok=False, status_code=None, error=str(exc))

    if resp.status_code != 200:
        return ResultadoFetch(ok=False, status_code=resp.status_code, error=f"HTTP {resp.status_code}")

    soup = BeautifulSoup(resp.text, "lxml")

    titulo = None
    if soup.title and soup.title.string:
        titulo = soup.title.string.strip()

    fecha = None
    for tag_name, attrs in META_FECHA_TAGS:
        tag = soup.find(tag_name, attrs=attrs)
        if tag and tag.get("content"):
            fecha = tag["content"]
            break

    # Extraccion de texto: quitar scripts/estilos
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    # RF5/RF8: Enfocar la extraccion en el contenido principal para evitar clasificar
    # en base a titulares de otras noticias o publicidad en el sidebar/footer.
    nodo_principal = soup.find("article") or soup.find("main")
    
    if nodo_principal:
        # Usamos un soup temporal para borrar cosas irrelevantes SIN afectar
        # la busqueda de enlaces (los enlaces del menu siguen sirviendo para el crawling)
        temp_soup = BeautifulSoup(str(nodo_principal), "lxml")
        for tag in temp_soup(["aside", "footer", "header", "nav", "form"]):
            tag.decompose()
        texto = re.sub(r"\s+", " ", temp_soup.get_text(separator=" ")).strip()
    else:
        # Si es una portada (homepage como ESPN) donde no hay <article>, extraemos todo normal
        texto = re.sub(r"\s+", " ", soup.get_text(separator=" ")).strip()

    dominio_origen = (urlparse(url).hostname or "").lower()
    enlaces = []
    for a in soup.find_all("a", href=True):
        absoluta = urljoin(url, a["href"])
        parsed = urlparse(absoluta)
        dominio_enlace = (parsed.hostname or "").lower()
        dominio_raiz = dominio_enlace.removeprefix("www.")
        if (
            parsed.scheme in ("http", "https")
            and dominio_enlace == dominio_origen
            and dominio_raiz not in DOMINIOS_EXCLUIDOS
        ):
            parametros = parse_qs(parsed.query)
            if any(clave in parametros for clave in ("share", "utm_source", "gclid", "iu")):
                continue
            limpio = parsed._replace(query="", fragment="")
            enlace = urlunparse(limpio)
            if enlace != url and enlace not in enlaces:
                enlaces.append(enlace)
                if len(enlaces) >= MAX_ENLACES_POR_PAGINA:
                    break

    return ResultadoFetch(
        ok=True,
        status_code=resp.status_code,
        titulo=titulo,
        texto=texto,
        fecha_publicacion=fecha,
        enlaces=list(dict.fromkeys(enlaces)),  # dedup preservando orden
    )


def normalizar(texto: str) -> str:
    """Minusculas y sin tildes, usado por matching/identity/classification."""
    texto = texto.lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto
