"""Pruebas de normalización y extracción de horas."""

from __future__ import annotations

import unittest
from datetime import datetime

from cort.text import (
    contiene,
    despues_de,
    fecha_larga,
    hora_desde_texto,
    hora_larga,
    normalizar,
    proxima_ocurrencia,
    recortar,
    similitud,
)


class PruebasNormalizar(unittest.TestCase):
    def test_quita_tildes_mayusculas_y_puntuacion(self):
        self.assertEqual(normalizar("¡Hola, CORT! ¿Qué hora es?"), "hola cort que hora es")

    def test_conserva_dos_puntos_para_la_hora(self):
        self.assertEqual(normalizar("Alarma a las 6:30"), "alarma a las 6:30")

    def test_conserva_la_enie(self):
        self.assertEqual(normalizar("MAÑANA"), "manana")
        self.assertEqual(normalizar("mañana"), "manana")

    def test_texto_vacio(self):
        self.assertEqual(normalizar(None), "")
        self.assertEqual(normalizar("   "), "")


class PruebasContiene(unittest.TestCase):
    def test_no_activa_ram_dentro_de_programa(self):
        self.assertFalse(contiene(normalizar("abre el programa inventado"), "ram"))

    def test_activa_ram_como_palabra(self):
        self.assertTrue(contiene(normalizar("cuánta ram libre hay"), "ram"))

    def test_frase_completa(self):
        self.assertTrue(contiene(normalizar("decime qué hora es"), "que hora"))
        self.assertFalse(contiene(normalizar("la hora del té"), "que hora"))

    def test_despues_de_devuelve_el_resto(self):
        self.assertEqual(
            despues_de(normalizar("busca en youtube lofi"), "busca en youtube"),
            "lofi",
        )


class PruebasHora(unittest.TestCase):
    def test_dos_puntos(self):
        self.assertEqual(hora_desde_texto("alarma a las 6:30"), (6, 30))

    def test_y_media_y_cuarto(self):
        self.assertEqual(hora_desde_texto("a las 6 y media"), (6, 30))
        self.assertEqual(hora_desde_texto("a las 7 y cuarto"), (7, 15))

    def test_am_y_pm(self):
        self.assertEqual(hora_desde_texto("a las 7 pm"), (19, 0))
        self.assertEqual(hora_desde_texto("a las 12 am"), (0, 0))
        self.assertEqual(hora_desde_texto("a las 12 pm"), (12, 0))

    def test_parte_del_dia(self):
        self.assertEqual(hora_desde_texto(normalizar("9 de la noche")), (21, 0))
        self.assertEqual(hora_desde_texto(normalizar("6 de la mañana")), (6, 0))
        self.assertEqual(hora_desde_texto(normalizar("1 de la madrugada")), (1, 0))

    def test_sin_hora(self):
        self.assertIsNone(hora_desde_texto("programa una alarma"))
        self.assertIsNone(hora_desde_texto("mañana temprano"))

    def test_proxima_ocurrencia_salta_al_dia_siguiente(self):
        ahora = datetime(2026, 10, 27, 10, 0, 0)
        self.assertEqual(proxima_ocurrencia(6, 30, ahora), datetime(2026, 10, 28, 6, 30))
        self.assertEqual(proxima_ocurrencia(11, 0, ahora), datetime(2026, 10, 27, 11, 0))


class PruebasFormato(unittest.TestCase):
    def test_fecha_larga(self):
        self.assertEqual(fecha_larga(datetime(2026, 10, 27)), "martes 27 de octubre de 2026")

    def test_hora_larga(self):
        self.assertEqual(hora_larga(datetime(2026, 10, 27, 0, 53)), "12:53 de la madrugada")
        self.assertEqual(hora_larga(datetime(2026, 10, 27, 6, 5)), "6:05 de la mañana")
        self.assertEqual(hora_larga(datetime(2026, 10, 27, 12, 30)), "12:30 de la tarde")
        self.assertEqual(hora_larga(datetime(2026, 10, 27, 15, 30)), "3:30 de la tarde")
        self.assertEqual(hora_larga(datetime(2026, 10, 27, 21, 0)), "9:00 de la noche")

    def test_similitud_ignora_palabras_cortas(self):
        self.assertGreater(similitud("musica rock", "rock musica"), 0.5)
        self.assertEqual(similitud("", "algo"), 0.0)

    def test_recortar_respeta_el_limite(self):
        texto = recortar("a" * 50, limite=10)
        self.assertEqual(len(texto), 10)
        self.assertTrue(texto.endswith("…"))


if __name__ == "__main__":
    unittest.main()
