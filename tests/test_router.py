"""Pruebas del router determinista: cada frase debe caer en su intención."""

from __future__ import annotations

import unittest
from datetime import datetime

from cort.router import enrutar


def intencion(texto):
    return enrutar(texto)


class PruebasRouter(unittest.TestCase):
    def test_saludo_exacto(self):
        self.assertEqual(intencion("hola").nombre, "saludo")
        self.assertEqual(intencion("Buenos días").nombre, "saludo")

    def test_quita_la_palabra_de_activacion(self):
        intento = intencion("Cort, ¿qué hora es?")
        self.assertEqual(intento.nombre, "hora")

    def test_hora_y_fecha(self):
        self.assertEqual(intencion("¿qué hora es?").nombre, "hora")
        self.assertEqual(intencion("¿qué día es hoy?").nombre, "fecha")

    def test_sistema(self):
        self.assertEqual(intencion("cómo está la PC").nombre, "sistema")
        self.assertEqual(intencion("cuánta RAM queda").nombre, "sistema")

    def test_programa_no_es_ram(self):
        intento = intencion("abre el programa inventado")
        self.assertEqual(intento.nombre, "app")
        self.assertEqual(intento.args["nombre"], "programa inventado")

    def test_alarma_con_dos_puntos_conserva_el_mensaje(self):
        intento = intencion("alarma a las 6:30 con ir a MORFO 3")
        self.assertEqual(intento.nombre, "alarma")
        self.assertEqual(intento.args["hora"], (6, 30))
        self.assertIn("morfo 3", intento.args["mensaje"])
        self.assertNotIn("30 ir", intento.args["mensaje"])
        cuando = datetime.fromisoformat(intento.args["cuando"])
        self.assertEqual((cuando.hour, cuando.minute), (6, 30))

    def test_alarma_sin_hora_pide_la_hora(self):
        self.assertEqual(intencion("programa una alarma").nombre, "alarma_sin_hora")
        self.assertEqual(intencion("recuérdame algo").nombre, "alarma_sin_hora")

    def test_alarma_con_hora_y_mensaje(self):
        intento = intencion("recuérdame comprar pan a las 8")
        self.assertEqual(intento.nombre, "alarma")
        self.assertEqual(intento.args["hora"], (8, 0))
        self.assertIn("comprar pan", intento.args["mensaje"])

    def test_arnes_explicito_gana_a_clima(self):
        intento = intencion("usa el arnés para investigar el clima")
        self.assertEqual(intento.nombre, "arnes")
        self.assertEqual(intento.args["objetivo"], "investigar el clima")

    def test_arnes_por_verbo(self):
        self.assertEqual(intencion("investiga sobre la urea").nombre, "arnes")

    def test_clima_con_ciudad(self):
        intento = intencion("clima en Caracas")
        self.assertEqual(intento.nombre, "clima")
        self.assertEqual(intento.args["ciudad"], "caracas")

    def test_abrir_app(self):
        intento = intencion("abre la calculadora")
        self.assertEqual(intento.nombre, "app")
        self.assertEqual(intento.args["nombre"], "calculadora")

    def test_busqueda_en_youtube(self):
        intento = intencion("busca en YouTube lofi")
        self.assertEqual(intento.nombre, "buscar")
        self.assertEqual(intento.args["motor"], "youtube")
        self.assertEqual(intento.args["consulta"], "lofi")

    def test_busqueda_en_google(self):
        intento = intencion("busca recetas de arepas")
        self.assertEqual(intento.nombre, "buscar")
        self.assertEqual(intento.args["motor"], "google")
        self.assertEqual(intento.args["consulta"], "recetas de arepas")

    def test_memoria(self):
        intento = intencion("me llamo Sandra")
        self.assertEqual(intento.nombre, "recordar")
        self.assertEqual(intento.args, {"clave": "nombre", "valor": "sandra"})

        intento = intencion("vivo en Caracas")
        self.assertEqual(intento.nombre, "recordar")
        self.assertEqual(intento.args["clave"], "ciudad")

        self.assertEqual(intencion("¿cómo me llamo?").nombre, "consultar_memoria")
        self.assertEqual(intencion("olvida mi color favorito").nombre, "olvidar")

    def test_nota_conserva_tildes_y_no_usa_articulos_como_clave(self):
        intento = intencion("recuerda que la práctica es el jueves")
        self.assertEqual(intento.nombre, "recordar")
        self.assertEqual(intento.args["clave"], "nota practica")
        self.assertEqual(intento.args["valor"], "la práctica es el jueves")

    def test_medios(self):
        self.assertEqual(intencion("pausa").nombre, "media_pausa")
        self.assertEqual(intencion("reanuda").nombre, "media_reanudar")
        self.assertEqual(intencion("siguiente canción").nombre, "media_siguiente")
        self.assertEqual(intencion("sube el volumen").args["delta"], 10)
        self.assertEqual(intencion("baja el volumen").args["delta"], -10)

    def test_conocimiento(self):
        intento = intencion("¿qué sabes de la urea?")
        self.assertEqual(intento.nombre, "conocimiento")
        self.assertIn("urea", intento.args["tema"])

    def test_silencio_y_ayuda(self):
        self.assertEqual(intencion("silencio").nombre, "silencio")
        self.assertEqual(intencion("ayuda").nombre, "ayuda")

    def test_modelos_de_ollama(self):
        intento = intencion("¿qué modelos tienes en Ollama?")
        self.assertEqual(intento.nombre, "modelos_listar")

        intento = intencion("descarga el modelo qwen3:0.6b")
        self.assertEqual(intento.nombre, "modelo_descargar")
        self.assertEqual(intento.args["nombre"], "qwen3:0.6b")

        intento = intencion("instala qwen2.5:1.5b")
        self.assertEqual(intento.nombre, "modelo_descargar")
        self.assertEqual(intento.args["nombre"], "qwen2.5:1.5b")

        intento = intencion("usa el modelo llama3.2")
        self.assertEqual(intento.nombre, "modelo_usar")
        self.assertEqual(intento.args["nombre"], "llama3.2")

        intento = intencion("cambia al modelo qwen3:0.6b")
        self.assertEqual(intento.nombre, "modelo_usar")
        self.assertEqual(intento.args["nombre"], "qwen3:0.6b")

        intento = intencion("cancela la descarga del modelo")
        self.assertEqual(intento.nombre, "modelo_cancelar")

    def test_olvidar_el_contexto_no_borra_hechos(self):
        intento = intencion("olvida la conversación")
        self.assertEqual(intento.nombre, "contexto_limpiar")
        intento = intencion("olvida mi color favorito")
        self.assertEqual(intento.nombre, "olvidar")
        self.assertEqual(intento.args["clave"], "color favorito")

    def test_guarda_gustos_personales(self):
        intento = intencion("mi color favorito es el azul")
        self.assertEqual(intento.nombre, "recordar")
        self.assertEqual(intento.args["clave"], "color favorito")
        self.assertEqual(intento.args["valor"], "azul")

    def test_frase_libre_va_al_modelo(self):
        self.assertIsNone(intencion("explícame la fotosíntesis con un ejemplo"))


if __name__ == "__main__":
    unittest.main()
