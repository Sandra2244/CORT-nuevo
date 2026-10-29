"""Pruebas del servidor del HUD: estáticos, API y rechazo de rutas fuera de lugar."""

from __future__ import annotations

import http.client
import json
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from cort.app import Cort
from cort.hud.server import Servidor
from tests.soporte import config_de_prueba


class PruebasServidorHud(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.cfg = config_de_prueba(Path(cls._tmp.name))
        cls.app = Cort(cls.cfg, voz=False)
        cls.app.memoria._db.execute("PRAGMA synchronous=OFF")
        cls.app.memoria._db.execute("PRAGMA journal_mode=MEMORY")
        cls.servidor = Servidor(cls.app, puerto=0)
        cls.url = cls.servidor.iniciar()

    @classmethod
    def tearDownClass(cls):
        cls.servidor.detener()
        cls.app.cerrar()
        cls._tmp.cleanup()

    # --- utilidades -----------------------------------------------------
    def _get(self, ruta: str) -> tuple[int, bytes, str]:
        with urllib.request.urlopen(self.url + ruta.lstrip("/"), timeout=5) as r:
            return r.status, r.read(), r.headers.get("Content-Type", "")

    def _post(self, ruta: str, datos: dict) -> tuple[int, dict]:
        cuerpo = json.dumps(datos).encode("utf-8")
        req = urllib.request.Request(
            self.url + ruta.lstrip("/"),
            data=cuerpo,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read())

    # --- estáticos ------------------------------------------------------
    def test_index(self):
        estado, cuerpo, tipo = self._get("/")
        self.assertEqual(estado, 200)
        self.assertIn(b"CORT", cuerpo)
        self.assertIn("text/html", tipo)

    def test_css(self):
        estado, cuerpo, tipo = self._get("/static/hud.css")
        self.assertEqual(estado, 200)
        self.assertIn(b"--cyan", cuerpo)
        self.assertIn("text/css", tipo)

    def test_manifest_para_instalar_en_android(self):
        estado, cuerpo, tipo = self._get("/static/manifest.webmanifest")
        self.assertEqual(estado, 200)
        self.assertIn("application/manifest+json", tipo)
        datos = json.loads(cuerpo)
        self.assertEqual(datos["short_name"], "CORT")
        self.assertEqual(datos["display"], "standalone")
        self.assertEqual(len(datos["icons"]), 2)

    def test_icono_pwa(self):
        estado, cuerpo, tipo = self._get("/static/icons/icon-192.png")
        self.assertEqual(estado, 200)
        self.assertEqual(tipo, "image/png")
        self.assertGreater(len(cuerpo), 1000)

    def test_ruta_inexistente(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/no-existe")
        self.assertEqual(ctx.exception.code, 404)

    def test_no_sale_de_la_carpeta_estatica(self):
        conexion = http.client.HTTPConnection("127.0.0.1", self.servidor.puerto, timeout=5)
        try:
            conexion.request("GET", "/static/../cort/__init__.py")
            respuesta = conexion.getresponse()
            respuesta.read()
        finally:
            conexion.close()
        self.assertEqual(respuesta.status, 403)

    # --- API ------------------------------------------------------------
    def test_salud(self):
        estado, cuerpo, _ = self._get("/api/salud")
        self.assertEqual(estado, 200)
        self.assertTrue(json.loads(cuerpo)["ok"])

    def test_estado(self):
        estado, cuerpo, _ = self._get("/api/estado")
        self.assertEqual(estado, 200)
        datos = json.loads(cuerpo)
        for clave in ("hora", "fecha", "estado", "mensajes", "metricas", "voz", "alarmas"):
            self.assertIn(clave, datos)
        self.assertRegex(datos["hora"], r"^\d{2}:\d{2}:\d{2}$")

    def test_modelos_responde_con_estado(self):
        estado, cuerpo, _ = self._get("/api/modelos")
        self.assertEqual(estado, 200)
        datos = json.loads(cuerpo)
        for clave in ("ok", "disponible", "activo", "modelos", "motivo", "recomendados", "progreso"):
            self.assertIn(clave, datos)
        self.assertIsInstance(datos["modelos"], list)
        self.assertTrue(datos["recomendados"])
        if not datos["ok"]:
            self.assertTrue(datos["motivo"])

    def test_capacidades_agrupadas(self):
        estado, cuerpo, _ = self._get("/api/capacidades")
        self.assertEqual(estado, 200)
        datos = json.loads(cuerpo)
        self.assertTrue(datos["ok"])
        self.assertGreaterEqual(datos["total"], 11)
        self.assertTrue(datos["categorias"])
        nombres = []
        for categoria in datos["categorias"]:
            self.assertTrue(categoria["id"])
            self.assertTrue(categoria["nombre"])
            self.assertTrue(categoria["herramientas"])
            for tool in categoria["herramientas"]:
                self.assertTrue(tool["nombre"])
                self.assertTrue(tool["descripcion"])
                self.assertTrue(tool["ejemplo"])
                nombres.append(tool["nombre"])
        self.assertIn("hora", nombres)
        self.assertEqual(len(nombres), datos["total"])

    def test_accion_detener_corta_el_turno(self):
        estado, datos = self._post("/api/accion", {"accion": "detener"})
        self.assertEqual(estado, 200)
        self.assertTrue(datos["ok"])
        self.assertEqual(datos["mensaje"], "Turno detenido.")
        self.assertTrue(self.app.ollama._turno.is_set())
        # El turno siguiente limpia la cancelación y responde normalmente.
        estado, datos = self._post("/api/chat", {"texto": "¿qué hora es?"})
        self.assertEqual(estado, 200)
        self.assertEqual(datos["herramienta"], "hora")

    def test_cancelar_sin_descarga_lo_dice(self):
        estado, datos = self._post("/api/modelos/cancelar", {})
        self.assertEqual(estado, 200)
        self.assertFalse(datos["ok"])
        self.assertIn("No hay ninguna descarga", datos["error"])

    def test_seleccionar_modelo_invalido_no_falla(self):
        estado, datos = self._post("/api/modelos/seleccionar", {"nombre": "x; rm -rf /"})
        self.assertEqual(estado, 200)
        self.assertFalse(datos["ok"])
        self.assertIn("inválido", datos["error"])

    def test_chat_responde_por_el_router(self):
        estado, datos = self._post("/api/chat", {"texto": "¿qué hora es?"})
        self.assertEqual(estado, 200)
        self.assertEqual(datos["herramienta"], "hora")
        self.assertIn("Son las", datos["respuesta"])

    def test_chat_vacio_es_400(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._post("/api/chat", {"texto": "   "})
        self.assertEqual(ctx.exception.code, 400)

    def test_accion_silencio(self):
        estado, datos = self._post("/api/accion", {"accion": "silencio", "activar": True})
        self.assertEqual(estado, 200)
        self.assertTrue(datos["silencio"])
        self.assertTrue(self.app.tts.silencio)
        self._post("/api/accion", {"accion": "silencio", "activar": False})
        self.assertFalse(self.app.tts.silencio)

    def test_accion_desconocida(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._post("/api/accion", {"accion": "borrar-todo"})
        self.assertEqual(ctx.exception.code, 400)


if __name__ == "__main__":
    unittest.main()
