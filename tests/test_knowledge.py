"""Pruebas de la lectura de apuntes locales en knowledge/."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cort.tools import knowledge
from tests.soporte import contexto_de_prueba

APUNTE = (
    "El ciclo de la urea ocurre en el hígado y convierte el amoníaco en urea. "
    "Es la vía principal para eliminar el nitrógeno del cuerpo."
)


class PruebasConocimiento(unittest.TestCase):
    def setUp(self):
        knowledge._CACHE.clear()
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.carpeta = self.base / "knowledge"
        self.ctx = contexto_de_prueba(self.base)

    def tearDown(self):
        self.ctx.memoria.cerrar()
        self._tmp.cleanup()
        knowledge._CACHE.clear()

    def _escribir(self, nombre: str, contenido: str) -> None:
        self.carpeta.mkdir(parents=True, exist_ok=True)
        (self.carpeta / nombre).write_text(contenido, encoding="utf-8")

    def test_sin_carpeta_avisa(self):
        self.assertIn("No hay apuntes", knowledge.buscar(self.ctx, "urea"))

    def test_lee_markdown_y_txt(self):
        self._escribir("biologia.md", APUNTE)
        self._escribir("notas.txt", "Recordatorio: la práctica de laboratorio es el jueves a las nueve.")
        texto = knowledge.buscar(self.ctx, "ciclo urea")
        self.assertIn("biologia.md", texto)
        self.assertIn("hígado", texto)

    def test_ignora_readme(self):
        self._escribir("README.md", APUNTE)
        self.assertIn("No hay apuntes", knowledge.buscar(self.ctx, "urea"))

    def test_ignora_parrafos_muy_cortos(self):
        self._escribir("corto.md", "urea")
        self.assertIn("No hay apuntes", knowledge.buscar(self.ctx, "urea"))

    def test_busqueda_sin_resultados(self):
        self._escribir("biologia.md", APUNTE)
        self.assertIn("No encontré", knowledge.buscar(self.ctx, "termodinámica"))

    def test_contexto_para_el_modelo(self):
        self._escribir("biologia.md", APUNTE)
        contexto = knowledge.contexto(self.ctx, "ciclo de la urea")
        self.assertIn("ciclo de la urea", contexto)
        self.assertIn("[biologia.md]", contexto)

    def test_contexto_sin_coincidencias(self):
        self._escribir("biologia.md", APUNTE)
        self.assertEqual(knowledge.contexto(self.ctx, "álgebra lineal"), "")

    def test_tema_vacio_pide_tema(self):
        self._escribir("biologia.md", APUNTE)
        self.assertIn("¿Sobre qué", knowledge.buscar(self.ctx, ""))


if __name__ == "__main__":
    unittest.main()
