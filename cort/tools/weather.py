"""Clima real sin claves: ip-api.com para ubicación y open-meteo.com para el tiempo."""

from __future__ import annotations

import time

import requests

CABECERAS = {"User-Agent": "CORT/0.1 (asistente local)"}
_CACHE: dict[str, tuple[float, str]] = {}

CODIGOS = {
    0: "despejado",
    1: "mayormente despejado",
    2: "parcialmente nublado",
    3: "nublado",
    45: "niebla",
    48: "niebla con escarcha",
    51: "llovizna ligera",
    53: "llovizna moderada",
    55: "llovizna intensa",
    56: "llovizna helada",
    57: "llovizna helada intensa",
    61: "lluvia ligera",
    63: "lluvia moderada",
    65: "lluvia intensa",
    66: "lluvia helada",
    67: "lluvia helada intensa",
    71: "nieve ligera",
    73: "nieve moderada",
    75: "nieve intensa",
    77: "granos de nieve",
    80: "chubascos ligeros",
    81: "chubascos moderados",
    82: "chubascos violentos",
    85: "chubascos de nieve",
    86: "chubascos de nieve fuertes",
    95: "tormenta",
    96: "tormenta con granizo",
    99: "tormenta fuerte con granizo",
}

FALLO_CLIMA = (
    "No puedo consultar el clima real en este momento, probablemente por falta de "
    "conexión a internet. Prefiero decirle esto antes que inventar un dato."
)


def _json(url: str, params: dict | None = None) -> dict | None:
    try:
        r = requests.get(url, params=params, headers=CABECERAS, timeout=6)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:  # noqa: BLE001
        return None


def _ubicacion_por_ip() -> dict | None:
    datos = _json(
        "http://ip-api.com/json/",
        {"fields": "status,message,city,regionName,country,lat,lon", "lang": "es"},
    )
    if not datos or datos.get("status") != "success":
        return None
    return datos


def _geocodificar(ciudad: str) -> dict | None:
    datos = _json(
        "https://geocoding-api.open-meteo.com/v1/search",
        {"name": ciudad, "count": 1, "language": "es", "format": "json"},
    )
    if not datos or not datos.get("results"):
        return None
    r = datos["results"][0]
    return {
        "city": r.get("name", ciudad),
        "regionName": r.get("admin1", ""),
        "country": r.get("country", ""),
        "lat": r.get("latitude"),
        "lon": r.get("longitude"),
    }


def _pronostico(lat: float, lon: float) -> dict | None:
    return _json(
        "https://api.open-meteo.com/v1/forecast",
        {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,"
            "precipitation,weather_code,wind_speed_10m",
            "timezone": "auto",
            "forecast_days": 1,
        },
    )


def _formatear(lugar: dict, pron: dict) -> str:
    actual = pron.get("current") or {}
    temp = actual.get("temperature_2m")
    sens = actual.get("apparent_temperature")
    hum = actual.get("relative_humidity_2m")
    viento = actual.get("wind_speed_10m")
    codigo = actual.get("weather_code")
    cielo = CODIGOS.get(int(codigo), "sin descripción") if codigo is not None else "sin datos"
    nombre = lugar.get("city") or "tu zona"
    region = lugar.get("regionName") or ""
    pais = lugar.get("country") or ""
    sitio = ", ".join(p for p in (nombre, region, pais) if p)
    if temp is None:
        return FALLO_CLIMA
    return (
        f"En {sitio} hay {temp} °C (sensación {sens} °C), humedad {hum} %, "
        f"viento {viento} km/h y cielo {cielo}."
    )


def clima(ctx=None, ciudad: str = "") -> str:
    ciudad = (ciudad or "").strip()
    if not ciudad and getattr(ctx, "memoria", None):
        ciudad = (ctx.memoria.hecho("ciudad") or "").strip()
    cache_min = 10
    if ctx is not None:
        cache_min = int(ctx.cfg.get("clima.cache_min", 10))
    clave_cache = f"clima:{ciudad.lower()}"
    ahora = time.time()
    if clave_cache in _CACHE and ahora - _CACHE[clave_cache][0] < cache_min * 60:
        return _CACHE[clave_cache][1]

    if ciudad:
        lugar = _geocodificar(ciudad)
        if not lugar:
            return (
                f"No encontré la ciudad «{ciudad}». Probá con otro nombre o revisá la "
                "conexión; no voy a inventar el clima."
            )
    else:
        lugar = _ubicacion_por_ip()
        if not lugar:
            return FALLO_CLIMA

    if lugar.get("lat") is None or lugar.get("lon") is None:
        return FALLO_CLIMA
    pron = _pronostico(float(lugar["lat"]), float(lugar["lon"]))
    if not pron:
        return FALLO_CLIMA
    texto = _formatear(lugar, pron)
    _CACHE[clave_cache] = (ahora, texto)
    if ctx is not None:
        ctx.log(f"clima · {lugar.get('city', '?')}")
    return texto
