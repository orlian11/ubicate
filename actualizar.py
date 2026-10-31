#!/usr/bin/env python3
"""
Actualizador de eventos CABA para Uber.
- SIN APIs pagas ni claves: descarga páginas web públicas y extrae los datos.
- NUNCA inventa datos: si una fuente falla, queda registrada en "fuentes" y no se rellena nada.
- Genera eventos.json (lo lee index.html). Pensado para correr en GitHub Actions cada pocas horas.

Uso local:  python actualizar.py          (modo normal)
            python actualizar.py -v       (muestra detalle de cada fuente para depurar)
"""
import json, re, sys, unicodedata, datetime as dt
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse, parse_qs, quote_plus
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

VERBOSE = "-v" in sys.argv
TZ = ZoneInfo("America/Argentina/Buenos_Aires")
DIAS_ADELANTE = 7          # cuántos días hacia adelante mostrar
SOLO_LUGARES_CONOCIDOS = True   # recitales: solo lugares de la tabla LUGARES
ARCHIVO_SALIDA = "eventos.json"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "es-AR,es;q=0.9",
}

# ───────────────────────── FUENTES (editá acá) ─────────────────────────
# Recitales / teatros: páginas con datos estructurados (JSON-LD). Agregá más URLs cuando quieras.
FUENTES_JSONLD = [
    ("Songkick Buenos Aires", "https://www.songkick.com/es/metro-areas/32911-argentina-buenos-aires", 3),
    ("Songkick Rock",         "https://www.songkick.com/es/metro-areas/32911-argentina-buenos-aires/genre/rock", 2),
    ("Songkick Latin",        "https://www.songkick.com/es/metro-areas/32911-argentina-buenos-aires/genre/latin", 2),
    ("Songkick Movistar Arena", "https://www.songkick.com/es/venues/4150369-movistar-arena", 2),
    # (nombre, url, cantidad_de_paginas)
]
# Fútbol: se buscan notas recientes con "días y horarios" y se leen los partidos de los clubes de la tabla.
FUTBOL_BUSQUEDAS = [