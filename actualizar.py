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
    "Liga Profesional fecha días y horarios",
    "Liga Profesional programación horarios partidos Clausura",
    "Boca River Vélez San Lorenzo Huracán horario partido",
]
FUTBOL_URLS_MANUALES = []   # podés pegar acá URLs de notas con la programación de la fecha

# ───────────────────────── TABLAS PROPIAS (verificá/ajustá) ─────────────────────────
# capacidad aproximada → se usa para calcular la importancia (no es dato inventado por IA, es regla tuya).
LUGARES = [
    {"nombre": "Movistar Arena", "alias": ["movistar arena"], "dir": "Humboldt 450, Villa Crespo", "cap": 15000},
    {"nombre": "Luna Park", "alias": ["luna park"], "dir": "Av. Eduardo Madero 470, San Nicolás", "cap": 8500},
    {"nombre": "Teatro Gran Rex", "alias": ["gran rex"], "dir": "Av. Corrientes 857, San Nicolás", "cap": 3300},
    {"nombre": "Teatro Ópera", "alias": ["teatro opera", "opera orbis", "opera allianz"], "dir": "Av. Corrientes 860, San Nicolás", "cap": 2300},
    {"nombre": "Teatro Colón", "alias": ["teatro colon"], "dir": "Cerrito 628, Microcentro", "cap": 2500},
    {"nombre": "Teatro Vorterix", "alias": ["vorterix"], "dir": "Av. Federico Lacroze 3455, Colegiales", "cap": 2000},
    {"nombre": "Estadio Obras", "alias": ["estadio obras", "obras sanitarias"], "dir": "Av. del Libertador 7395, Núñez", "cap": 4000},
    {"nombre": "Groove", "alias": ["groove"], "dir": "Av. Santa Fe 4389, Palermo", "cap": 2000},
    {"nombre": "La Trastienda", "alias": ["la trastienda"], "dir": "Balcarce 460, San Telmo", "cap": 1000},
    {"nombre": "Hipódromo de Palermo", "alias": ["hipodromo de palermo", "hipodromo argentino"], "dir": "Av. del Libertador 4101, Palermo", "cap": 20000},
    {"nombre": "Estadio Mas Monumental (River)", "alias": ["monumental", "river plate", "estadio river"], "dir": "Av. Pres. Figueroa Alcorta 7597, Núñez", "cap": 85000},
    {"nombre": "La Bombonera (Boca)", "alias": ["bombonera", "alberto j armando", "estadio boca"], "dir": "Brandsen 805, La Boca", "cap": 57000},
    {"nombre": "José Amalfitani (Vélez)", "alias": ["amalfitani", "estadio velez"], "dir": "Av. Juan B. Justo 9200, Liniers", "cap": 49000},
]
# Clubes: alias → (nombre, estadio, dirección, capacidad). Solo se toman partidos donde el club es LOCAL.
CLUBES = {
    "boca": ("Boca Juniors", "La Bombonera", "Brandsen 805, La Boca", 57000),
    "boca juniors": ("Boca Juniors", "La Bombonera", "Brandsen 805, La Boca", 57000),
    "river": ("River Plate", "Estadio Mas Monumental", "Av. Pres. Figueroa Alcorta 7597, Núñez", 85000),
    "river plate": ("River Plate", "Estadio Mas Monumental", "Av. Pres. Figueroa Alcorta 7597, Núñez", 85000),
    "velez": ("Vélez Sarsfield", "José Amalfitani", "Av. Juan B. Justo 9200, Liniers", 49000),
    "velez sarsfield": ("Vélez Sarsfield", "José Amalfitani", "Av. Juan B. Justo 9200, Liniers", 49000),
    "san lorenzo": ("San Lorenzo", "Nuevo Gasómetro", "Av. Perito Moreno 7000, Bajo Flores", 47000),
    "huracan": ("Huracán", "Tomás A. Ducó", "Av. Amancio Alcorta 2570, Parque Patricios", 48000),
    "racing": ("Racing Club", "Presidente Perón (Avellaneda)", "Estadio Presidente Perón, Avellaneda", 51000),
    "racing club": ("Racing Club", "Presidente Perón (Avellaneda)", "Estadio Presidente Perón, Avellaneda", 51000),
    "independiente": ("Independiente", "Libertadores de América (Avellaneda)", "Av. Bochini 751, Avellaneda", 52000),
    "argentinos": ("Argentinos Juniors", "Diego A. Maradona", "Gavilán 2151, La Paternal", 26000),
    "argentinos juniors": ("Argentinos Juniors", "Diego A. Maradona", "Gavilán 2151, La Paternal", 26000),
    "platense": ("Platense", "Ciudad de Vicente López", "Vicente López, Buenos Aires", 25000),
    "barracas central": ("Barracas Central", "Claudio Fabián Tapia", "Barracas, CABA", 7000),
    "deportivo riestra": ("Deportivo Riestra", "Guillermo Laza", "Nueva Pompeya, CABA", 3000),
    "riestra": ("Deportivo Riestra", "Guillermo Laza", "Nueva Pompeya, CABA", 3000),
}
GRANDES = {"Boca Juniors", "River Plate", "Racing Club", "Independiente", "San Lorenzo"}
# Otros rivales (solo para mostrar el nombre bien escrito)
OTROS_EQUIPOS = ["Estudiantes", "Gimnasia", "Lanús", "Banfield", "Tigre", "Talleres", "Belgrano", "Instituto",
                 "Newell's", "Rosario Central", "Godoy Cruz", "Unión", "Colón", "Sarmiento", "Central Córdoba",
                 "Defensa y Justicia", "Atlético Tucumán", "Independiente Rivadavia", "Aldosivi", "Gimnasia (Mza.)",
                 "Estudiantes (RC)", "Argentinos", "Platense", "Huracán", "Barracas Central"]

DURACION_H = {"futbol": 2.0, "recital": 2.75, "teatro": 2.0, "otro": 2.5}

# ───────────────────────── utilidades ─────────────────────────
def log(*a):
    if VERBOSE: print(*a)

def norm(s):
    s = unicodedata.normalize("NFD", (s or "").lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", s)).strip()

def bajar(url, intentos=2, timeout=25):
    ultimo = None
    for _ in range(intentos):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout)
            if r.status_code == 200 and r.text:
                return r.text
            ultimo = f"HTTP {r.status_code}"
        except Exception as e:
            ultimo = str(e)[:120]
    raise RuntimeError(ultimo)

def buscar_lugar(*textos):
    t = " ".join(norm(x) for x in textos if x)
    for l in LUGARES:
        if any(a in t for a in l["alias"]):
            return l
    return None

def importancia(cap, local=None, visitante=None):
    if local in GRANDES and visitante in GRANDES: return "Crítica"   # clásicos / partidos grandes
    if cap is None: return "Media"
    if cap >= 40000: return "Crítica"
    if cap >= 10000: return "Alta"
    if cap >= 3000: return "Media"
    return "Baja"

def armar(tipo, titulo, fecha, hora, lugar, direccion, cap, fuente, url, **extra):
    salida = None
    if hora:
        ini = dt.datetime.combine(fecha, dt.time.fromisoformat(hora))
        salida = (ini + dt.timedelta(hours=DURACION_H.get(tipo, 2.5))).strftime("%H:%M")
    ev = {"tipo": tipo, "titulo": titulo, "fecha": fecha.isoformat(), "hora": hora,
          "salida_estimada": salida, "lugar": lugar, "direccion": direccion, "capacidad": cap,
          "importancia": importancia(cap, extra.get("local"), extra.get("visitante")),
          "fuente": fuente, "url": url}
    ev.update({k: v for k, v in extra.items() if v})
    return ev

# ───────────────────────── recitales / teatros (JSON-LD) ─────────────────────────
def _iso(s):
    s = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", s.strip().replace("Z", "+00:00"))
    return s

def parse_fecha_iso(valor):
    """Devuelve (date, 'HH:MM' o None) en hora argentina."""
    if not valor: return None, None
    v = str(valor).strip()
    if len(v) == 10:
        return dt.date.fromisoformat(v), None
    d = dt.datetime.fromisoformat(_iso(v))
    if d.tzinfo: d = d.astimezone(TZ)
    return d.date(), d.strftime("%H:%M")

def _nombres(x):
    if not x: return []
    if isinstance(x, str): return [x]
    if isinstance(x, dict): return [x.get("name")] if x.get("name") else []
    if isinstance(x, list): return [n for i in x for n in _nombres(i)]
    return []

def _recorrer(nodo):
    if isinstance(nodo, list):
        for i in nodo: yield from _recorrer(i)
    elif isinstance(nodo, dict):
        yield nodo
        for k in ("@graph", "itemListElement", "item"):
            if k in nodo: yield from _recorrer(nodo[k])

def extraer_jsonld(html, fuente, url_base):
    soup = BeautifulSoup(html, "lxml")
    out = []
    for s in soup.find_all("script", type="application/ld+json"):
        try: data = json.loads(s.string or s.get_text())
        except Exception: continue
        for d in _recorrer(data):
            tipo_ld = d.get("@type")
            tipos = tipo_ld if isinstance(tipo_ld, list) else [tipo_ld]
            if not any(t and "Event" in str(t) for t in tipos): continue
            try: fecha, hora = parse_fecha_iso(d.get("startDate"))
            except Exception: continue
            if not fecha or not d.get("name"): continue
            loc = d.get("location") or {}
            loc = loc[0] if isinstance(loc, list) and loc else loc
            nom_lugar = loc.get("name") if isinstance(loc, dict) else None
            addr = loc.get("address") if isinstance(loc, dict) else None
            addr = addr.get("streetAddress") if isinstance(addr, dict) else addr
            lugar = buscar_lugar(nom_lugar, addr)
            if SOLO_LUGARES_CONOCIDOS and not lugar: continue
            artistas = _nombres(d.get("performer")) or _nombres(d.get("name"))
            es_deporte = any("Sports" in str(t) for t in tipos)
            tipo = "futbol" if es_deporte else ("teatro" if any("Theater" in str(t) for t in tipos) else "recital")
            out.append(armar(tipo, str(d["name"]).strip(), fecha, hora,
                             lugar["nombre"] if lugar else (nom_lugar or "Lugar sin confirmar"),
                             lugar["dir"] if lugar else (addr or ""), lugar["cap"] if lugar else None,
                             fuente, d.get("url") if str(d.get("url", "")).startswith("http") else url_base,
                             artista=", ".join(artistas[:3])))
    return out

def recolectar_jsonld(estado):
    eventos = []
    for nombre, url, paginas in FUENTES_JSONLD:
        total, error = 0, None
        for p in range(1, paginas + 1):
            u = url if p == 1 else f"{url}?page={p}"
            try:
                evs = extraer_jsonld(bajar(u), nombre, u)
            except Exception as e:
                error = str(e); break
            log(f"[{nombre}] página {p}: {len(evs)} eventos")
            if not evs: break
            eventos += evs; total += len(evs)
        estado[nombre] = {"ok": error is None and total > 0, "cantidad": total,
                          **({"error": error} if error else ({} if total else {"error": "0 eventos (¿cambió la página o bloqueó?)"}))}
    return eventos

# ───────────────────────── fútbol (texto de notas con "días y horarios") ─────────────────────────
MESES = {m: i + 1 for i, m in enumerate("enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split())}
DIAS_SEM = {"lunes": 0, "martes": 1, "miercoles": 2, "jueves": 3, "viernes": 4, "sabado": 5, "domingo": 6}
RE_DIA = re.compile(r"(lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo)\s+(\d{1,2})\s*[°º]?\s+de\s+"
                    r"(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)", re.I)
RE_PARTIDO = re.compile(r"(\d{1,2})\s*[:.]\s*(\d{2})\s*(?:hs?\b\.?)?[\s|:\-]*"
                        r"([^\n|–—]{2,40}?)\s+(?:[–—-]|vs\.?)\s+([^\n|–—]{2,45})", re.I)

def limpiar_equipo(t):
    t = re.sub(r"\((?!RC|Mza)[^)]*\)", "", t)          # saca (Zona A), etc. (deja RC y Mza.)
    t = re.sub(r"\b(zona\s*[ab]|tnt|espn|fox|dsports|tv p[uú]blica|en vivo)\b.*", "", t, flags=re.I)
    return re.sub(r"\s+", " ", t).strip(" -–|:.")

def equipo_canonico(t):
    k = norm(t)
    if k in CLUBES: return CLUBES[k][0]
    for o in OTROS_EQUIPOS:
        if norm(o) == k: return o
    return None

def parsear_futbol(texto, hoy, fuente, url):
    """Devuelve lista de (fecha, hora, local, visitante, fuente, url) SOLO si ambos equipos son reconocidos
    y el día de la semana coincide con la fecha (control anti-errores)."""
    out = []
    marcas = list(RE_DIA.finditer(texto))
    for i, m in enumerate(marcas):
        dia_nom = norm(m.group(1)); dia = int(m.group(2)); mes = MESES[m.group(3).lower()]
        fecha = None
        for anio in (hoy.year, hoy.year + 1, hoy.year - 1):
            try:
                f = dt.date(anio, mes, dia)
            except ValueError:
                continue
            if f.weekday() == DIAS_SEM[dia_nom] and abs((f - hoy).days) < 200:
                fecha = f; break
        if not fecha: continue
        seg = texto[m.end(): marcas[i + 1].start() if i + 1 < len(marcas) else m.end() + 2500]
        for p in RE_PARTIDO.finditer(seg):
            h, mi = int(p.group(1)), int(p.group(2))
            if h > 23 or mi > 59: continue
            loc, vis = equipo_canonico(limpiar_equipo(p.group(3))), equipo_canonico(limpiar_equipo(p.group(4)))
            if loc and vis and loc != vis:
                out.append((fecha, f"{h:02d}:{mi:02d}", loc, vis, fuente, url))
    return out

def links_busqueda(consulta, max_dias=10, maximo=8):
    """Busca noticias recientes vía RSS de Bing (gratis, sin clave) y devuelve las URLs reales."""
    rss = bajar(f"https://www.bing.com/news/search?q={quote_plus(consulta)}&format=rss&setmkt=es-AR")
    soup = BeautifulSoup(rss, "xml")
    res, ahora = [], dt.datetime.now(dt.timezone.utc)
    for it in soup.find_all("item"):
        link = it.link.get_text(strip=True) if it.link else ""
        q = parse_qs(urlparse(link).query)
        real = q.get("url", [link])[0]
        try:
            pub = parsedate_to_datetime(it.pubDate.get_text(strip=True))
            if (ahora - pub).days > max_dias: continue
        except Exception:
            pass
        if real.startswith("http"): res.append(real)
    return res[:maximo]

def recolectar_futbol(estado, hoy):
    urls = list(FUTBOL_URLS_MANUALES)
    err_busq = None
    for q in FUTBOL_BUSQUEDAS:
        try: urls += links_busqueda(q)
        except Exception as e: err_busq = str(e)
    urls = list(dict.fromkeys(urls))
    log(f"[Fútbol] {len(urls)} notas candidatas")
    hallados, leidas = [], 0
    for u in urls:
        try:
            soup = BeautifulSoup(bajar(u, intentos=1, timeout=20), "lxml")
            for t in soup(["script", "style", "nav", "footer"]): t.decompose()
            texto = soup.get_text("\n")
        except Exception as e:
            log("  ✗", u, e); continue
        leidas += 1
        p = parsear_futbol(texto, hoy, urlparse(u).netloc.replace("www.", ""), u)
        log(f"  {urlparse(u).netloc}: {len(p)} partidos")
        hallados += p
    # consolidar: mismo partido en varias notas → se elige la hora con más coincidencias
    agrupado = {}
    for fecha, hora, loc, vis, fuente, url in hallados:
        agrupado.setdefault((fecha, loc, vis), {}).setdefault(hora, []).append((fuente, url))
    eventos = []
    for (fecha, loc, vis), horas in agrupado.items():
        if loc not in {v[0] for v in CLUBES.values()}: continue          # solo local con estadio en la tabla
        hora, fuentes = max(horas.items(), key=lambda kv: len(kv[1]))
        club = next(v for v in CLUBES.values() if v[0] == loc)
        ev = armar("futbol", f"{loc} vs {vis}", fecha, hora, club[1], club[2], club[3],
                   fuentes[0][0], fuentes[0][1], local=loc, visitante=vis)
        ev["coincidencias"] = len({f for f, _ in fuentes})
        if len(horas) > 1: ev["aviso"] = "Las fuentes difieren en el horario: confirmar"
        eventos.append(ev)
    estado["Fútbol (notas de prensa)"] = {
        "ok": bool(eventos), "cantidad": len(eventos), "notas_leidas": leidas,
        **({"error": err_busq or "0 partidos de clubes de la tabla"} if not eventos else {})}
    return eventos

# ───────────────────────── principal ─────────────────────────
def main():
    ahora = dt.datetime.now(TZ); hoy = ahora.date()
    estado, eventos = {}, []
    eventos += recolectar_jsonld(estado)
    eventos += recolectar_futbol(estado, hoy)

    limite = hoy + dt.timedelta(days=DIAS_ADELANTE)
    vistos, finales = set(), []
    for e in eventos:
        f = dt.date.fromisoformat(e["fecha"])
        if not (hoy <= f <= limite): continue
        clave = (e["fecha"], norm(e["lugar"])[:12], norm(e["titulo"])[:20])
        if clave in vistos: continue
        vistos.add(clave); finales.append(e)
    finales.sort(key=lambda e: (e["fecha"], e["hora"] or "99:99"))

    salida = {"actualizado": ahora.isoformat(timespec="minutes"), "fuentes": estado, "eventos": finales}
    if not finales:   # no pisar datos buenos con una lista vacía
        try:
            previo = json.load(open(ARCHIVO_SALIDA, encoding="utf-8"))
            if isinstance(previo, dict):
                vigentes = [e for e in previo.get("eventos", []) if dt.date.fromisoformat(e["fecha"]) >= hoy]
                if vigentes:
                    salida["eventos"] = vigentes
                    salida["aviso"] = f"No se pudo actualizar. Se muestran datos previos de {previo.get('actualizado')}."
        except Exception:
            pass
    json.dump(salida, open(ARCHIVO_SALIDA, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"{len(salida['eventos'])} eventos guardados. Fuentes:")
    for n, s in estado.items():
        print(f"  {'OK ' if s['ok'] else 'FALLÓ'} {n}: {s['cantidad']} {s.get('error', '')}")

if __name__ == "__main__":
    main()
