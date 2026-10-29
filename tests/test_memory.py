"""Pruebas de la memoria SQLite: hechos, episodios, alarmas y meta."""

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from cort.brain.memory import Memoria


class PruebasMemoria(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.memoria = Memoria(Path(self._tmp.name) / "cort.db")
        # En pruebas no hace falta durabilidad; sin esto cada commit espera al disco.
        self.memoria._db.execute("PRAGMA synchronous=OFF")
        self.memoria._db.execute("PRAGMA journal_mode=MEMORY")

    def tearDown(self):
        self.memoria.cerrar()
        self._tmp.cleanup()

    # --- hechos ---------------------------------------------------------
    def test_recordar_y_leer(self):
        self.memoria.recordar("Nombre", "  Sandra  ")
        self.assertEqual(self.memoria.hecho("nombre"), "Sandra")
        self.assertIsNone(self.memoria.hecho("ciudad"))

    def test_recordar_reemplaza(self):
        self.memoria.recordar("ciudad", "Caracas")
        self.memoria.recordar("ciudad", "Bogotá")
        self.assertEqual(self.memoria.hecho("ciudad"), "Bogotá")
        self.assertEqual(len(self.memoria.hechos()), 1)

    def test_olvidar_por_coincidencia(self):
        self.memoria.recordar("color favorito", "azul")
        self.memoria.recordar("comida favorita", "arepas")
        self.assertEqual(self.memoria.olvidar("color"), 1)
        self.assertIsNone(self.memoria.hecho("color favorito"))
        self.assertEqual(self.memoria.hecho("comida favorita"), "arepas")

    def test_valores_vacios_no_se_guardan(self):
        self.memoria.recordar("", "algo")
        self.memoria.recordar("algo", "   ")
        self.assertEqual(self.memoria.hechos(), [])

    # --- episodios ------------------------------------------------------
    def test_episodios_en_orden(self):
        self.memoria.agregar_episodio("user", "hola")
        self.memoria.agregar_episodio("assistant", "hola, te escucho")
        self.assertEqual(
            [e["texto"] for e in self.memoria.episodios(5)],
            ["hola", "hola, te escucho"],
        )

    def test_episodios_se_podan_a_500(self):
        for i in range(505):
            self.memoria.agregar_episodio("user", f"e{i}")
        todos = self.memoria.episodios(1000)
        self.assertEqual(len(todos), 500)
        self.assertEqual(todos[0]["texto"], "e5")
        self.assertEqual(todos[-1]["texto"], "e504")

    # --- alarmas --------------------------------------------------------
    def test_alarma_pendiente_solo_cuando_llega(self):
        pasado = datetime.now() - timedelta(minutes=1)
        futuro = datetime.now() + timedelta(hours=2)
        self.memoria.crear_alarma(pasado, "pasada")
        self.memoria.crear_alarma(futuro, "futura")
        pendientes = self.memoria.alarmas_pendientes()
        self.assertEqual([a["texto"] for a in pendientes], ["pasada"])

    def test_marcar_alarma_la_quita(self):
        alarma_id = self.memoria.crear_alarma(datetime.now() - timedelta(minutes=1), "ya")
        self.memoria.marcar_alarma(alarma_id)
        self.assertEqual(self.memoria.alarmas_pendientes(), [])

    def test_proximas_alarmas_en_orden(self):
        ahora = datetime.now()
        self.memoria.crear_alarma(ahora + timedelta(hours=3), "tercera")
        self.memoria.crear_alarma(ahora + timedelta(hours=1), "primera")
        self.assertEqual(
            [a["texto"] for a in self.memoria.proximas_alarmas(2)],
            ["primera", "tercera"],
        )

    def test_alarma_sin_texto_usa_es_hora(self):
        alarma_id = self.memoria.crear_alarma(datetime.now(), "   ")
        alarma = [a for a in self.memoria.proximas_alarmas(5) if a["id"] == alarma_id][0]
        self.assertEqual(alarma["texto"], "Es hora")

    # --- meta -----------------------------------------------------------
    def test_meta_guarda_y_actualiza(self):
        self.assertIsNone(self.memoria.meta("arranque"))
        self.memoria.meta("arranque", "2026-10-27")
        self.assertEqual(self.memoria.meta("arranque"), "2026-10-27")
        self.memoria.meta("arranque", "2026-10-28")
        self.assertEqual(self.memoria.meta("arranque"), "2026-10-28")


if __name__ == "__main__":
    unittest.main()
