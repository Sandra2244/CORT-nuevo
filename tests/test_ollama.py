"""Pruebas del cliente de Ollama con respuestas HTTP simuladas (sin red)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cort.brain.ollama import Ollama
from tests.soporte import RespuestaFalsa, config_de_prueba


class FlujoFalso:
    def __init__(self, textos: list[str], codigo: int = 200):
        self.status_code = codigo
        self.text = "detalle de error"
        self._textos = textos
        self.cerrado = False

    def iter_lines(self, decode_unicode=False):
        for texto in self._textos:
            yield json.dumps({"message": {"content": texto}})

    def close(self):
        self.cerrado = True


class FlujoDescarga:
    def __init__(self, lineas: list[dict], codigo: int = 200):
        self.status_code = codigo
        self.text = "detalle de error"
        self._lineas = lineas
        self.cerrado = False

    def iter_lines(self, decode_unicode=False):
        for dato in self._lineas:
            yield json.dumps(dato)

    def close(self):
        self.cerrado = True


class PruebasOllama(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.cfg = config_de_prueba(Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def test_disponible_y_modelos(self):
        with mock.patch(
            "cort.brain.ollama.requests.get",
            return_value=RespuestaFalsa({"models": [{"name": "qwen3:0.6b"}, {"name": "smollm2:135m"}]}),
        ):
            cliente = Ollama(self.cfg)
            self.assertTrue(cliente.disponible())
            self.assertEqual(cliente.modelos(), ["qwen3:0.6b", "smollm2:135m"])

    def test_modelos_info_con_tamano_y_familia(self):
        datos = {
            "models": [
                {
                    "name": "qwen3:0.6b",
                    "size": 639_000_000,
                    "modified_at": "2026-10-01T10:00:00Z",
                    "details": {"family": "qwen3", "parameter_size": "0.6B", "quantization_level": "Q4_K_M"},
                }
            ]
        }
        with mock.patch(
            "cort.brain.ollama.requests.get", return_value=RespuestaFalsa(datos)
        ):
            cliente = Ollama(self.cfg)
            info = cliente.modelos_info()
        self.assertTrue(cliente.ultimo_error == "")
        self.assertEqual(info[0]["nombre"], "qwen3:0.6b")
        self.assertEqual(info[0]["tamano_gb"], 0.6)
        self.assertEqual(info[0]["familia"], "qwen3")
        self.assertEqual(info[0]["parametros"], "0.6B")

    def test_nombre_de_modelo_invalido(self):
        cliente = Ollama(self.cfg)
        self.assertFalse(cliente.nombre_valido("qwen3; rm -rf /"))
        self.assertFalse(cliente.nombre_valido(""))
        self.assertTrue(cliente.nombre_valido("qwen3:0.6b"))
        self.assertTrue(cliente.nombre_valido("hf.co/usuario/modelo:Q4"))

    def test_descargar_reporta_progreso(self):
        lineas = [
            {"status": "pulling manifest"},
            {"status": "pulling abc", "completed": 50, "total": 100},
            {"status": "success"},
        ]
        flujo = FlujoDescarga(lineas)
        vistos: list[dict] = []
        with mock.patch("cort.brain.ollama.requests.post", return_value=flujo):
            resultado = Ollama(self.cfg).descargar("qwen3:0.6b", al_progreso=vistos.append)
        self.assertTrue(resultado["ok"])
        self.assertEqual(resultado["modelo"], "qwen3:0.6b")
        self.assertEqual(resultado["estado"], "success")
        self.assertEqual(vistos[1]["porcentaje"], 50.0)
        self.assertTrue(flujo.cerrado)

    def test_descargar_rechaza_nombre_inseguro_sin_llamar(self):
        with mock.patch("cort.brain.ollama.requests.post") as post:
            resultado = Ollama(self.cfg).descargar("malo; rm -rf /")
        post.assert_not_called()
        self.assertFalse(resultado["ok"])
        self.assertIn("inválido", resultado["error"])

    def test_descargar_error_de_ollama(self):
        flujo = FlujoDescarga([{"error": "model not found"}])
        with mock.patch("cort.brain.ollama.requests.post", return_value=flujo):
            resultado = Ollama(self.cfg).descargar("nope:1b")
        self.assertFalse(resultado["ok"])
        self.assertIn("model not found", resultado["error"])

    def test_descargar_suma_capas(self):
        lineas = [
            {"status": "pulling manifest"},
            {"status": "pulling aaa", "digest": "a", "completed": 100, "total": 200},
            {"status": "pulling bbb", "digest": "b", "completed": 50, "total": 200},
            {"status": "success"},
        ]
        flujo = FlujoDescarga(lineas)
        vistos: list[dict] = []
        with mock.patch("cort.brain.ollama.requests.post", return_value=flujo):
            resultado = Ollama(self.cfg).descargar("qwen3:0.6b", al_progreso=vistos.append)
        self.assertTrue(resultado["ok"])
        # 150 de 400 en la última línea con totales
        self.assertEqual(vistos[2]["porcentaje"], 37.5)
        self.assertEqual(vistos[2]["total"], 400)
        self.assertEqual(vistos[2]["capas"], 2)
        # la línea success cierra en 100
        self.assertEqual(vistos[-1]["porcentaje"], 100.0)
        self.assertTrue(vistos[-1]["terminado"])

    def test_descargar_se_puede_cancelar(self):
        cliente = Ollama(self.cfg)
        flujo = FlujoDescarga(
            [
                {"status": "pulling aaa", "digest": "a", "completed": 1, "total": 100},
                {"status": "pulling aaa", "digest": "a", "completed": 50, "total": 100},
                {"status": "success"},
            ]
        )
        vistos: list[dict] = []

        def progreso(dato):
            vistos.append(dato)
            cliente.cancelar_descarga()

        with mock.patch("cort.brain.ollama.requests.post", return_value=flujo):
            resultado = cliente.descargar("qwen3:0.6b", al_progreso=progreso)
        self.assertFalse(resultado["ok"])
        self.assertTrue(resultado.get("cancelado"))
        self.assertEqual(len(vistos), 1)
        self.assertTrue(flujo.cerrado)

    def test_sin_servidor(self):
        with mock.patch(
            "cort.brain.ollama.requests.get", side_effect=OSError("conexión rechazada")
        ):
            cliente = Ollama(self.cfg)
            self.assertFalse(cliente.disponible())
            self.assertEqual(cliente.ultimo_error, "OSError")

    def test_elegir_respaldo_si_falta_el_configurado(self):
        with mock.patch(
            "cort.brain.ollama.requests.get",
            return_value=RespuestaFalsa({"models": [{"name": "smollm2:135m"}, {"name": "qwen2.5:0.5b"}]}),
        ):
            cliente = Ollama(self.cfg)
            self.assertEqual(cliente.elegir_modelo(), "qwen2.5:0.5b")

    def test_elegir_el_mas_pequeno_si_no_hay_coincidencia(self):
        cfg = config_de_prueba(
            Path(self._tmp.name),
            cerebro={"modelo": "no-existe", "respaldo": "tampoco", "modelo_profundo": "nada"},
        )
        with mock.patch(
            "cort.brain.ollama.requests.get",
            return_value=RespuestaFalsa({"models": [{"name": "smollm2:135m"}]}),
        ):
            cliente = Ollama(cfg)
            self.assertEqual(cliente.elegir_modelo(), "smollm2:135m")

    def test_conversar_une_el_stream(self):
        cliente = Ollama(self.cfg)
        cliente.modelo = "smollm2:135m"
        vistos: list[str] = []
        with mock.patch(
            "cort.brain.ollama.requests.post",
            return_value=FlujoFalso(["Hola, ", "Sandra."]),
        ):
            texto = cliente.conversar([{"role": "user", "content": "hola"}], al_token=vistos.append)
        self.assertEqual(texto, "Hola, Sandra.")
        self.assertEqual(vistos, ["Hola, ", "Sandra."])

    def test_conversar_se_puede_detener(self):
        cliente = Ollama(self.cfg)
        cliente.modelo = "smollm2:135m"
        flujo = FlujoFalso(["uno ", "dos ", "tres"])
        vistos: list[str] = []

        def al_token(trozo):
            vistos.append(trozo)
            cliente.cancelar_turno()

        with mock.patch("cort.brain.ollama.requests.post", return_value=flujo):
            texto = cliente.conversar([{"role": "user", "content": "hola"}], al_token=al_token)
        self.assertTrue(cliente.cancelado)
        self.assertEqual(texto, "uno")
        self.assertEqual(vistos, ["uno "])
        self.assertTrue(flujo.cerrado)

    def test_limpiar_cancelacion_permite_otro_turno(self):
        cliente = Ollama(self.cfg)
        cliente.modelo = "smollm2:135m"
        cliente.cancelar_turno()
        cliente.limpiar_cancelacion()
        with mock.patch(
            "cort.brain.ollama.requests.post",
            return_value=FlujoFalso(["completo"]),
        ):
            texto = cliente.conversar([{"role": "user", "content": "hola"}])
        self.assertEqual(texto, "completo")
        self.assertFalse(cliente.cancelado)

    def test_404_reintenta_con_otro_modelo(self):
        cliente = Ollama(self.cfg)
        cliente.modelo = "modelo-que-no-esta"
        respuestas = [
            FlujoFalso([], codigo=404),
            FlujoFalso(["Respuesta del respaldo."]),
        ]
        with mock.patch(
            "cort.brain.ollama.requests.post", side_effect=respuestas
        ), mock.patch(
            "cort.brain.ollama.requests.get",
            return_value=RespuestaFalsa({"models": [{"name": "qwen2.5:0.5b"}]}),
        ):
            texto = cliente.conversar([{"role": "user", "content": "hola"}])
        self.assertEqual(texto, "Respuesta del respaldo.")
        self.assertEqual(cliente.modelo, "qwen2.5:0.5b")

    def test_sin_modelo_no_llama(self):
        cfg = config_de_prueba(
            Path(self._tmp.name),
            cerebro={"modelo": "", "respaldo": "", "modelo_profundo": ""},
        )
        cliente = Ollama(cfg)
        with mock.patch(
            "cort.brain.ollama.requests.get", return_value=RespuestaFalsa({"models": []})
        ), mock.patch("cort.brain.ollama.requests.post") as post:
            self.assertEqual(cliente.conversar([{"role": "user", "content": "hola"}]), "")
        post.assert_not_called()
        self.assertEqual(cliente.ultimo_error, "sin modelo")

    def test_error_de_red_al_conversar(self):
        cliente = Ollama(self.cfg)
        cliente.modelo = "smollm2:135m"
        with mock.patch(
            "cort.brain.ollama.requests.post", side_effect=OSError("sin servidor")
        ):
            self.assertEqual(cliente.conversar([{"role": "user", "content": "hola"}]), "")
        self.assertIn("OSError", cliente.ultimo_error)


if __name__ == "__main__":
    unittest.main()
