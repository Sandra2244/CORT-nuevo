"""Pruebas del arnés de agentes con un modelo falso (sin red)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cort.brain.harness import Arnes, _extraer_json
from cort.bus import Bus
from cort.tools.base import Tool
from tests.soporte import config_de_prueba, contexto_de_prueba


class OllamaGuion:
    """Devuelve respuestas preparadas en orden; no toca la red."""

    def __init__(self, respuestas: list[str], modelo: str = "falso"):
        self.respuestas = list(respuestas)
        self.modelo = modelo
        self.ultimo_error = ""
        self.mensajes: list[list[dict]] = []

    def elegir_modelo(self) -> str:
        return self.modelo

    def conversar(self, mensajes, al_token=None, modelo=None):
        self.mensajes.append(list(mensajes))
        return self.respuestas.pop(0) if self.respuestas else ""


class PruebasExtraerJson(unittest.TestCase):
    def test_json_limpio(self):
        self.assertEqual(_extraer_json('{"tool": "hora", "args": {}}'), {"tool": "hora", "args": {}})

    def test_json_rodeado_de_texto(self):
        dato = _extraer_json('Claro. {"herramienta": "clima", "args": {"ciudad": "Caracas"}} listo')
        self.assertEqual(dato["herramienta"], "clima")

    def test_respuesta_simple(self):
        self.assertEqual(_extraer_json('{"respuesta": "Listo"}'), {"respuesta": "Listo"})

    def test_json_ajeno_se_ignora(self):
        self.assertIsNone(_extraer_json('{"foo": 1}'))

    def test_texto_sin_json(self):
        self.assertIsNone(_extraer_json("No necesito herramientas."))

    def test_json_incompleto(self):
        self.assertIsNone(_extraer_json('{"tool": '))


class PruebasArnes(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.cfg = config_de_prueba(self.base)
        self.ctx = contexto_de_prueba(self.base)
        self.registro = self._registro()
        self.pasos: list[str] = []

    def tearDown(self):
        self.ctx.memoria.cerrar()
        self._tmp.cleanup()

    def _registro(self):
        from cort.tools.base import Registro

        registro = Registro()
        registro.registrar(
            Tool(
                "eco",
                "devuelve el texto recibido",
                {"type": "object", "properties": {"texto": {"type": "string"}}},
                lambda texto="": self.pasos.append(texto) or f"eco:{texto}",
            )
        )
        return registro

    def test_ejecuta_herramienta_y_responde(self):
        ollama = OllamaGuion(
            [
                '{"tool": "eco", "args": {"texto": "hola"}}',
                '{"respuesta": "Terminado."}',
            ]
        )
        arnes = Arnes(ollama, self.registro, self.cfg, Bus())
        respuesta, pasos = arnes.ejecutar("probá la herramienta", self.ctx)

        self.assertEqual(respuesta, "Terminado.")
        self.assertEqual(pasos, ["paso 1 · eco"])
        self.assertEqual(self.pasos, ["hola"])
        # el resultado de la herramienta vuelve al modelo en el segundo turno
        self.assertTrue(any("eco:hola" in m["content"] for m in ollama.mensajes[1]))

    def test_respuesta_sin_herramientas(self):
        ollama = OllamaGuion(['{"respuesta": "No hace falta nada."}'])
        arnes = Arnes(ollama, self.registro, self.cfg, Bus())
        respuesta, pasos = arnes.ejecutar("hola", self.ctx)
        self.assertEqual(respuesta, "No hace falta nada.")
        self.assertEqual(pasos, [])

    def test_texto_plano_se_devuelve(self):
        ollama = OllamaGuion(["La respuesta es 42."])
        arnes = Arnes(ollama, self.registro, self.cfg, Bus())
        respuesta, pasos = arnes.ejecutar("cuánto es 6x7", self.ctx)
        self.assertEqual(respuesta, "La respuesta es 42.")
        self.assertEqual(pasos, [])

    def test_sin_modelo_no_intenta(self):
        ollama = OllamaGuion([], modelo="")
        arnes = Arnes(ollama, self.registro, self.cfg, Bus())
        respuesta, pasos = arnes.ejecutar("algo", self.ctx)
        self.assertIn("No tengo un modelo de lenguaje", respuesta)
        self.assertEqual(pasos, [])

    def test_se_detiene_al_agotar_pasos(self):
        ollama = OllamaGuion(['{"tool": "eco", "args": {"texto": "x"}}'] * 3)
        arnes = Arnes(ollama, self.registro, self.cfg, Bus())
        respuesta, pasos = arnes.ejecutar("repite", self.ctx)
        self.assertIn("sin pasos", respuesta)
        self.assertEqual(len(pasos), 3)

    def test_herramienta_desconocida_al_ultimo_paso(self):
        ollama = OllamaGuion(
            [
                '{"tool": "eco", "args": {"texto": "a"}}',
                '{"tool": "eco", "args": {"texto": "b"}}',
                '{"tool": "inexistente", "args": {}}',
            ]
        )
        arnes = Arnes(ollama, self.registro, self.cfg, Bus())
        respuesta, pasos = arnes.ejecutar("falla", self.ctx)
        self.assertIn("El arnés se detuvo", respuesta)
        self.assertIn("No existe la herramienta", respuesta)
        self.assertEqual(len(pasos), 3)


if __name__ == "__main__":
    unittest.main()
