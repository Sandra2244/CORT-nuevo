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


class _AppSinNada:
    """Sustituto de `Cort` para probar el arranque del servidor sin núcleo."""

    def __init__(self, cfg):
        self.cfg = cfg


class PruebasLlaveDelHud(unittest.TestCase):
    """Quién entra al HUD cuando está abierto a la red: decides por IP, no por fe."""

    class _Llamada:
        """Lo justo de un handler: dirección del cliente, cabeceras y ruta."""

        def __init__(self, ip, token, headers=None, path="/api/estado"):
            self.client_address = (ip, 43210)
            self.token = token
            self.headers = headers or {}
            self.path = path

    def _pasa(self, **datos):
        from cort.hud.server import _Handler

        return _Handler._autorizado(self._Llamada(**datos))

    def test_la_pc_se_entra_sola(self):
        self.assertTrue(self._pasa(ip="127.0.0.1", token=""))
        self.assertTrue(self._pasa(ip="127.0.0.42", token=""))
        self.assertTrue(self._pasa(ip="::1", token="llave"))

    def test_la_red_sin_llave_configurada_no_entra(self):
        self.assertFalse(self._pasa(ip="192.168.1.50", token=""))
        self.assertFalse(self._pasa(ip="192.168.1.50", token="", path="/"))

    def test_la_red_con_llave_entre_por_cabecera_o_por_enlace(self):
        self.assertTrue(self._pasa(ip="192.168.1.50", token="abc123",
                                   headers={"X-CORT-Token": "abc123"}))
        self.assertTrue(self._pasa(ip="192.168.1.50", token="abc123",
                                   path="/?token=abc123"))

    def test_la_llave_equivocada_no_cuela(self):
        self.assertFalse(self._pasa(ip="192.168.1.50", token="abc123",
                                    headers={"X-CORT-Token": "abc1234"}))
        self.assertFalse(self._pasa(ip="192.168.1.50", token="abc123",
                                    headers={"X-CORT-Token": ""}, path="/?token="))
        self.assertFalse(self._pasa(ip="192.168.1.50", token="",
                                    headers={"X-CORT-Token": "cualquiera"}))

    def test_llave_con_tilde_por_enlace(self):
        # `compare_digest` con `str` revienta si hay tildes; aquí van en bytes.
        self.assertTrue(self._pasa(ip="192.168.1.50", token="cañón",
                                   path="/?token=ca%C3%B1%C3%B3n"))

    def test_la_ropa_de_la_pagina_no_pide_llave(self):
        from cort.hud.server import ruta_publica

        for ruta in ("/static/hud.js", "/static/hud.css", "/favicon.ico", "/api/salud"):
            self.assertTrue(ruta_publica(ruta), ruta)
        for ruta in ("/", "/index.html", "/api/estado", "/api/chat", "/api/modelos"):
            self.assertFalse(ruta_publica(ruta), ruta)

    def test_sin_llave_no_se_abre_a_la_red(self):
        from cort.hud.server import Servidor

        cfg = config_de_prueba(Path(tempfile.mkdtemp()))
        servidor = Servidor(_AppSinNada(cfg), host="0.0.0.0", puerto=0)
        with self.assertRaises(RuntimeError) as ctx:
            servidor.iniciar()
        self.assertIn("token", str(ctx.exception))

    def test_el_enlace_del_telefono_lleva_la_llave(self):
        from cort.hud.server import Servidor

        cfg = config_de_prueba(Path(tempfile.mkdtemp()), hud={"token": "llave123"})
        servidor = Servidor(_AppSinNada(cfg), host="0.0.0.0", puerto=8765)
        enlace = servidor.url_para_red()
        if enlace:  # sin ruta a la red no hay IP que anunciar: no se inventa
            self.assertTrue(enlace.endswith("?token=llave123"), enlace)
            self.assertIn(":8765/", enlace)
        else:
            self.assertEqual(Servidor.ip_de_red(), "")


@unittest.skipUnless(Servidor.ip_de_red(), "este equipo no tiene IP de red")
class PruebasLlavePorHTTP(unittest.TestCase):
    """La prueba de verdad: entrar desde la interfaz de la red, no desde el bucle."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.ip = Servidor.ip_de_red()
        cls.cfg = config_de_prueba(Path(cls._tmp.name), hud={"token": "llave-prueba"})
        cls.app = Cort(cls.cfg, voz=False)
        cls.servidor = Servidor(cls.app, host=cls.ip, puerto=0)
        cls.servidor.iniciar()
        cls.base = f"http://{cls.ip}:{cls.servidor.puerto}"

    @classmethod
    def tearDownClass(cls):
        cls.servidor.detener()
        cls.app.cerrar()
        cls._tmp.cleanup()

    def _codigo(self, ruta: str, cabeceras=None, datos=None) -> int:
        req = urllib.request.Request(
            self.base + ruta,
            data=json.dumps(datos).encode("utf-8") if datos is not None else None,
            headers=cabeceras or {},
            method="POST" if datos is not None else "GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status
        except urllib.error.HTTPError as e:
            return e.code

    def test_sin_llave_el_hud_y_la_api_no_abren(self):
        self.assertEqual(self._codigo("/"), 401)
        self.assertEqual(self._codigo("/api/estado"), 401)
        self.assertEqual(self._codigo("/api/accion", datos={"accion": "silencio"}), 401)

    def test_con_llave_entra_por_cabecera(self):
        self.assertEqual(self._codigo("/api/estado", {"X-CORT-Token": "llave-prueba"}), 200)

    def test_la_ropa_se_sirve_igual(self):
        self.assertEqual(self._codigo("/static/hud.css"), 200)
        self.assertEqual(self._codigo("/api/salud"), 200)


if __name__ == "__main__":
    unittest.main()
