"""Pruebas de integración del núcleo: router + memoria + estado del HUD."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cort.app import SIN_CEREBRO, Cort
from cort.tools import CATEGORIAS
from tests.soporte import config_de_prueba


class PruebasCort(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.cfg = config_de_prueba(Path(self._tmp.name))
        self.app = Cort(self.cfg, voz=False)
        # Sin esperas de disco: estas pruebas no comprueban durabilidad.
        self.app.memoria._db.execute("PRAGMA synchronous=OFF")
        self.app.memoria._db.execute("PRAGMA journal_mode=MEMORY")

    def tearDown(self):
        self.app.cerrar()
        self._tmp.cleanup()

    def test_saludo(self):
        datos = self.app.responder("hola")
        self.assertEqual(datos["respuesta"], "Hola. Te escucho.")
        self.assertEqual(datos["herramienta"], "")

    def test_hora_real(self):
        datos = self.app.responder("¿qué hora es?")
        self.assertEqual(datos["herramienta"], "hora")
        self.assertRegex(datos["respuesta"], r"Son las .+ \(\d{2}:\d{2}:\d{2}\)\.")

    def test_memoria_de_ida_y_vuelta(self):
        self.app.responder("me llamo sandra")
        datos = self.app.responder("¿cómo me llamo?")
        self.assertEqual(datos["herramienta"], "memoria")
        self.assertIn("Sandra", datos["respuesta"])
        self.assertNotIn("nombre:", datos["respuesta"])

    def test_nota_y_consulta(self):
        datos = self.app.responder("recuerda que la práctica es el jueves")
        self.assertIn("Guardé la nota", datos["respuesta"])
        self.assertIn("práctica", datos["respuesta"])
        consulta = self.app.responder("memoria")
        self.assertIn("nota: la práctica es el jueves", consulta["respuesta"])

    def test_app_fuera_de_la_lista_no_abre_nada(self):
        with mock.patch("cort.tools.apps.subprocess.Popen") as popen:
            datos = self.app.responder("abre el programa inventado")
        popen.assert_not_called()
        self.assertIn("lista permitida", datos["respuesta"])

    def test_alarma_sin_hora_pide_hora(self):
        datos = self.app.responder("programa una alarma")
        self.assertEqual(datos["herramienta"], "alarma")
        self.assertIn("¿A qué hora", datos["respuesta"])
        self.assertEqual(self.app.memoria.proximas_alarmas(), [])

    def test_sin_ollama_avisa_con_honestidad(self):
        with mock.patch.object(self.app.ollama, "disponible", return_value=False):
            datos = self.app.responder("explícame la fotosíntesis")
        self.assertEqual(datos["herramienta"], "sin_cerebro")
        self.assertEqual(datos["respuesta"], SIN_CEREBRO)

    def test_silencio_cambia_la_bandera(self):
        self.app.responder("silencio")
        self.assertTrue(self.app.tts.silencio)
        self.app.responder("habla")
        self.assertFalse(self.app.tts.silencio)

    def test_estado_hud(self):
        self.app.responder("hola")
        estado = self.app.estado_hud()
        self.assertIn("hora", estado)
        self.assertIn("version", estado)
        self.assertEqual(estado["mensajes"][-1]["rol"], "cort")
        self.assertIn("voz", estado)

    def test_episodios_se_guardan(self):
        self.app.responder("hola")
        episodios = self.app.memoria.episodios(5)
        self.assertEqual([e["rol"] for e in episodios], ["user", "assistant"])

    def test_texto_vacio(self):
        datos = self.app.responder("   ")
        self.assertIn("No te escuché", datos["respuesta"])

    def test_publica_evento_de_ejecucion(self):
        datos = self.app.responder("¿qué hora es?")
        self.assertGreaterEqual(datos["evento"]["id"], 1)
        self.assertEqual(datos["evento"]["tipo"], "ejecucion")
        self.assertEqual(self.app.estado_hud()["eventos"][-1]["tipo"], "ejecucion")

    def test_evento_de_ejecucion_trae_detalle(self):
        datos = self.app.responder("¿qué hora es?")
        detalle = datos["evento"]["detalle"]
        self.assertEqual(detalle["herramienta"], "hora")
        self.assertTrue(detalle["ok"])
        self.assertEqual(detalle["via"], "router")
        self.assertGreaterEqual(detalle["ms"], 0)
        self.assertFalse(detalle["cancelado"])

    def test_stop_corta_el_turno_y_no_lo_guarda(self):
        def conversar_falso(mensajes, al_token=None, **kwargs):
            self.app.detener_turno()
            self.app.ollama.cancelado = True
            return "respuesta a medias"

        with mock.patch.object(self.app.ollama, "disponible", return_value=True), mock.patch.object(
            self.app.ollama, "conversar", side_effect=conversar_falso
        ):
            datos = self.app.responder("explícame la fotosíntesis")
        self.assertEqual(datos["herramienta"], "detenido")
        self.assertIn("turno detenido", datos["respuesta"])
        self.assertEqual(self.app.estado_hud()["estado"], "idle")
        self.assertEqual([e["rol"] for e in self.app.memoria.episodios(5)], ["user"])

    def test_todas_las_herramientas_tienen_categoria_y_ejemplo(self):
        registro = self.app.registro
        for nombre in registro.nombres():
            tool = registro.obtener(nombre)
            self.assertTrue(tool.ejemplo, f"falta ejemplo en {nombre}")
            self.assertIn(tool.categoria, CATEGORIAS, f"categoría desconocida en {nombre}")

    def test_listar_modelos_sin_ollama(self):
        with mock.patch.object(self.app.ollama, "modelos_info", return_value=[]), mock.patch.object(
            self.app.ollama, "ultimo_error", "OSError"
        ):
            datos = self.app.responder("¿qué modelos tienes en Ollama?")
        self.assertIn("No puedo consultar Ollama", datos["respuesta"])
        self.assertIn("(error)", datos["herramienta"])

    def test_seleccionar_modelo_instalado(self):
        with mock.patch.object(
            self.app.ollama,
            "modelos_info",
            return_value=[{"nombre": "qwen3:0.6b", "tamano_gb": 0.6}],
        ):
            datos = self.app.seleccionar_modelo("qwen3")
        self.assertTrue(datos["ok"])
        self.assertEqual(self.app.ollama.modelo, "qwen3:0.6b")
        self.assertEqual(self.app.memoria.meta("modelo"), "qwen3:0.6b")

    def test_seleccionar_modelo_inexistente(self):
        with mock.patch.object(
            self.app.ollama,
            "modelos_info",
            return_value=[{"nombre": "qwen3:0.6b", "tamano_gb": 0.6}],
        ):
            datos = self.app.seleccionar_modelo("llama3.2")
        self.assertFalse(datos["ok"])
        self.assertIn("no está instalado", datos["error"])

    def test_descargar_modelo_guarda_el_activo(self):
        with mock.patch.object(
            self.app.ollama, "descargar", return_value={"ok": True, "modelo": "qwen3:0.6b"}
        ), mock.patch.object(
            self.app.ollama, "modelos_info", return_value=[{"nombre": "qwen3:0.6b", "tamano_gb": 0.6}]
        ):
            self.app.ollama.modelo = "otro:1b"
            datos = self.app.descargar_modelo("qwen3:0.6b")
        self.assertTrue(datos["ok"])
        self.assertEqual(datos["activo"], "qwen3:0.6b")
        self.assertEqual(self.app.ollama.modelo, "qwen3:0.6b")
        self.assertEqual(self.app.memoria.meta("modelo"), "qwen3:0.6b")
        self.assertEqual(self.app.estado_hud()["estado"], "idle")

    def test_descargar_publica_progreso_en_el_estado(self):
        def descarga(nombre, al_progreso=None):
            al_progreso({"estado": "pulling", "porcentaje": 42.0, "completado": 42, "total": 100})
            return {"ok": False, "error": "corte de red"}

        with mock.patch.object(self.app.ollama, "descargar", side_effect=descarga):
            datos = self.app.descargar_modelo("qwen3:0.6b")
        self.assertFalse(datos["ok"])
        estado = self.app.estado_hud()
        self.assertEqual(estado["descarga"]["porcentaje"], 42.0)
        self.assertEqual(estado["descarga"]["estado"], "error")

    def test_descargar_cancelada_no_es_error(self):
        with mock.patch.object(
            self.app.ollama,
            "descargar",
            return_value={"ok": False, "cancelado": True, "error": "Descarga cancelada."},
        ):
            datos = self.app.descargar_modelo("qwen3:0.6b")
        self.assertTrue(datos["cancelado"])
        self.assertEqual(self.app.estado_hud()["estado"], "idle")
        self.assertEqual(self.app.estado_hud()["descarga"]["estado"], "cancelada")

    def test_historial_se_reenvia_al_modelo(self):
        capturado: list[list[dict]] = []

        def conversar(mensajes, al_token=None, modelo=None, num_predict=None):
            capturado.append(mensajes)
            return "respuesta " + str(len(capturado))

        with mock.patch.object(self.app.ollama, "disponible", return_value=True), mock.patch.object(
            self.app.ollama, "conversar", side_effect=conversar
        ):
            self.app.responder("primera pregunta")
            self.app.responder("segunda pregunta")
        segunda = capturado[1]
        contenidos = [m["content"] for m in segunda]
        self.assertIn("primera pregunta", contenidos)
        self.assertIn("respuesta 1", contenidos)
        self.assertEqual(segunda[-1]["content"], "segunda pregunta")
        self.assertEqual(len(self.app._historial), 4)

    def test_modelo_pequeno_usa_prompt_compacto(self):
        capturado: list[list[dict]] = []

        def conversar(mensajes, al_token=None, modelo=None, num_predict=None):
            capturado.append((mensajes, num_predict))
            return "ok"

        with mock.patch.object(self.app.ollama, "disponible", return_value=True), mock.patch.object(
            self.app.ollama, "conversar", side_effect=conversar
        ):
            self.app.ollama.modelo = "qwen2.5:0.5b"
            self.app.responder("explícame el ciclo de la urea")
            self.app.ollama.modelo = "qwen3.5:2b"
            self.app.responder("explícame el ciclo de la urea")
        sistema_pequeno, limite_pequeno = capturado[0]
        sistema_grande, limite_grande = capturado[1]
        self.assertNotIn("Reglas inquebrantables", sistema_pequeno[0]["content"])
        self.assertIn("una o dos frases", sistema_pequeno[0]["content"])
        self.assertEqual(limite_pequeno, 120)
        self.assertIn("Reglas inquebrantables", sistema_grande[0]["content"])
        self.assertIsNone(limite_grande)

    def test_limpiar_contexto_descarta_el_historial(self):
        with mock.patch.object(self.app.ollama, "disponible", return_value=True), mock.patch.object(
            self.app.ollama, "conversar", return_value="ok"
        ):
            self.app.responder("hola, hablemos")
        self.assertTrue(self.app._historial)
        datos = self.app.responder("olvida la conversación")
        self.assertEqual(datos["herramienta"], "contexto")
        self.assertEqual(self.app._historial, [])

    def test_descargar_rechaza_nombre_inseguro(self):
        with mock.patch.object(self.app.ollama, "descargar") as descargar:
            datos = self.app.descargar_modelo("x; rm -rf /")
        descargar.assert_not_called()
        self.assertFalse(datos["ok"])


if __name__ == "__main__":
    unittest.main()
