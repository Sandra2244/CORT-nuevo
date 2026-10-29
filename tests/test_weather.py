"""Pruebas del clima: sin red debe fallar con honestidad, nunca inventar."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cort.tools import weather
from tests.soporte import RespuestaFalsa, contexto_de_prueba


GEO = {
    "results": [
        {
            "name": "Caracas",
            "admin1": "Distrito Capital",
            "country": "Venezuela",
            "latitude": 10.48,
            "longitude": -66.9,
        }
    ]
}

PRONOSTICO = {
    "current": {
        "temperature_2m": 24.5,
        "apparent_temperature": 26.0,
        "relative_humidity_2m": 70,
        "precipitation": 0,
        "weather_code": 0,
        "wind_speed_10m": 12.3,
    }
}


class PruebasClima(unittest.TestCase):
    def setUp(self):
        weather._CACHE.clear()
        self._tmp = tempfile.TemporaryDirectory()
        self.ctx = contexto_de_prueba(Path(self._tmp.name))

    def tearDown(self):
        self.ctx.memoria.cerrar()
        self._tmp.cleanup()
        weather._CACHE.clear()

    def test_sin_red_devuelve_el_mensaje_honesto(self):
        with mock.patch.object(weather.requests, "get", side_effect=OSError("sin red")):
            self.assertEqual(weather.clima(self.ctx), weather.FALLO_CLIMA)

    def test_ip_y_pronostico(self):
        respuestas = {
            "ip-api.com": RespuestaFalsa(
                {"status": "success", "city": "San Cristóbal", "regionName": "Táchira",
                 "country": "Venezuela", "lat": 7.77, "lon": -72.22}
            ),
            "geocoding-api": RespuestaFalsa(GEO),
            "api.open-meteo.com": RespuestaFalsa(PRONOSTICO),
        }

        def falso_get(url, params=None, headers=None, timeout=None):
            for clave, respuesta in respuestas.items():
                if clave in url:
                    return respuesta
            raise AssertionError(f"URL inesperada: {url}")

        with mock.patch.object(weather.requests, "get", side_effect=falso_get):
            texto = weather.clima(self.ctx)

        self.assertIn("San Cristóbal", texto)
        self.assertIn("24.5 °C", texto)
        self.assertIn("despejado", texto)
        self.assertNotEqual(texto, weather.FALLO_CLIMA)

    def test_ciudad_por_parametro_usa_geocodificacion(self):
        respuestas = {
            "geocoding-api": RespuestaFalsa(GEO),
            "api.open-meteo.com": RespuestaFalsa(PRONOSTICO),
        }

        def falso_get(url, params=None, headers=None, timeout=None):
            for clave, respuesta in respuestas.items():
                if clave in url:
                    return respuesta
            raise AssertionError(f"URL inesperada: {url}")

        with mock.patch.object(weather.requests, "get", side_effect=falso_get):
            texto = weather.clima(self.ctx, "Caracas")

        self.assertIn("Caracas", texto)
        self.assertIn("Venezuela", texto)

    def test_ciudad_guardada_en_memoria(self):
        self.ctx.memoria.recordar("ciudad", "Caracas")
        lugar = {"city": "Caracas", "regionName": "Distrito Capital", "country": "Venezuela",
                 "lat": 10.48, "lon": -66.9}
        with mock.patch.object(weather, "_geocodificar", return_value=lugar) as geo, \
             mock.patch.object(weather, "_pronostico", return_value=PRONOSTICO):
            texto = weather.clima(self.ctx)
        geo.assert_called_once_with("Caracas")
        self.assertIn("Caracas", texto)

    def test_ciudad_desconocida_no_inventa(self):
        with mock.patch.object(weather, "_geocodificar", return_value=None):
            texto = weather.clima(self.ctx, "Ciudad Inexistente")
        self.assertIn("No encontré la ciudad", texto)
        self.assertIn("no voy a inventar", texto)

    def test_cache_evita_repetir_la_consulta(self):
        lugar = {"city": "Caracas", "regionName": "Distrito Capital", "country": "Venezuela",
                 "lat": 10.48, "lon": -66.9}
        with mock.patch.object(weather, "_geocodificar", return_value=lugar), \
             mock.patch.object(weather, "_pronostico", return_value=PRONOSTICO) as pron:
            primero = weather.clima(self.ctx, "Caracas")
            segundo = weather.clima(self.ctx, "Caracas")
        self.assertEqual(primero, segundo)
        self.assertEqual(pron.call_count, 1)

    def test_temperatura_ausente_es_fallo(self):
        with mock.patch.object(weather, "_geocodificar", return_value=GEO["results"][0]), \
             mock.patch.object(weather, "_pronostico", return_value={"current": {}}):
            self.assertEqual(weather.clima(self.ctx, "Caracas"), weather.FALLO_CLIMA)


if __name__ == "__main__":
    unittest.main()
