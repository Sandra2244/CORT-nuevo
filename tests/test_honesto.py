"""Pruebas de la voz honesta: que no invente, que ofrezca salidas y que sea cálida."""

from __future__ import annotations

import unittest

from cort.brain import honesto, persona
from cort.brain.memory import Memoria
import tempfile
from pathlib import Path


class PruebasHonesto(unittest.TestCase):
    def test_cada_respuesta_admite_el_limite(self):
        casos = [
            (honesto.sin_modelo(), "no tengo el modelo de lenguaje"),
            (honesto.no_supe("no me alcanzó el tiempo"), "no lo sé"),
            (honesto.fallo_modelo("timeout"), "no logré"),
            (honesto.sin_pasos("paso 3 · clima"), "me quedé sin pasos"),
            (honesto.orden_dudosa("abre la puerta"), "no supe"),
        ]
        for texto, marca in casos:
            with self.subTest(marca=marca):
                self.assertIn(marca, texto.lower())

    def test_cada_respuesta_ofrece_salidas(self):
        for texto in (
            honesto.no_supe(),
            honesto.fallo_modelo(),
            honesto.sin_pasos(),
            honesto.orden_dudosa("x"),
        ):
            with self.subTest(texto=texto[:30]):
                self.assertRegex(texto.lower(), r"buscar|anotado|reintentar|intentamos")

    def test_no_supe_incluye_el_motivo_sin_repetir_el_punto(self):
        texto = honesto.no_supe("el modelo se quedó sin tiempo.")
        self.assertIn("No lo sé: el modelo se quedó sin tiempo.", texto)
        self.assertNotIn("..", texto)

    def test_sin_modelo_usa_los_ejemplos_que_le_pasan(self):
        texto = honesto.sin_modelo(["tocar el piano", "hacer café"])
        self.assertIn("tocar el piano o hacer café", texto)

    def test_sin_modelo_sin_ejemplos_no_queda_vacio(self):
        texto = honesto.sin_modelo([])
        self.assertIn("la hora y la fecha", texto)

    def test_fallo_modelo_agrega_detalle_entre_parentesis(self):
        self.assertIn("(timeout)", honesto.fallo_modelo("timeout"))
        self.assertNotIn("()", honesto.fallo_modelo(""))


class PruebasPersona(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.memoria = Memoria(Path(self._tmp.name) / "cort.db")

    def tearDown(self):
        self.memoria.cerrar()
        self._tmp.cleanup()

    def test_prompt_completo_tiene_protocolo_de_no_saber(self):
        texto = persona.construir(self.memoria)
        self.assertIn("No lo sé", texto)
        self.assertIn("Inventar es peor que no saber", texto)
        self.assertIn("mirar los apuntes", texto)

    def test_prompt_compacto_tambien_es_honesto(self):
        texto = persona.construir(self.memoria, compacto=True)
        self.assertIn("Si no sabés algo, decilo", texto)
        self.assertLess(len(texto), 1200, "un modelo de 0.5B no puede con un prompt largo")

    def test_prompt_usa_el_nombre_sin_repetirlo(self):
        self.memoria.recordar("nombre", "sandra")
        completo = persona.construir(self.memoria)
        self.assertIn("Hablás con Sandra.", completo)
        self.assertIn("nunca en cada frase", completo)
        compacto = persona.construir(self.memoria, compacto=True)
        self.assertIn("El usuario se llama Sandra", compacto)

    def test_sin_nombre_no_inventa_uno(self):
        self.assertNotIn("Hablás con", persona.construir(self.memoria))


if __name__ == "__main__":
    unittest.main()
