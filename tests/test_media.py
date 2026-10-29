"""Pruebas de reproducción local (sin lanzar VLC de verdad)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cort.tools import media
from tests.soporte import contexto_de_prueba


class PopenFalso:
    def __init__(self):
        self.pid = 4242

    def poll(self):
        return None


class PruebasMedia(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.cfg = None
        self.ctx = contexto_de_prueba(self.base)
        self.cfg = self.ctx.cfg
        self.playlists = Path(self.cfg.playlists_dir)
        self.playlists.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.ctx.memoria.cerrar()
        self._tmp.cleanup()

    def _crear(self, relativo: str) -> Path:
        destino = self.playlists / relativo
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(b"falso")
        return destino

    def test_consulta_vacia_pregunta(self):
        self.assertIn("¿Qué querés", media.reproducir(self.ctx, ""))

    def test_musica_reproduce_toda_la_carpeta(self):
        self._crear("Rock/a.mp3")
        self._crear("Rock/b.mp3")
        with mock.patch.object(media.subprocess, "Popen", return_value=PopenFalso()) as popen:
            texto = media.reproducir(self.ctx, "música")
        cmd = popen.call_args.args[0]
        self.assertEqual(cmd[0], "cvlc")
        self.assertIn("--no-video", cmd)
        self.assertEqual(sum(1 for c in cmd if c.endswith(".mp3")), 2)
        self.assertIn("tu música", texto)
        self.assertIn("(2 archivos)", texto)

    def test_playlist_por_carpeta(self):
        self._crear("Rock/una.mp3")
        with mock.patch.object(media.subprocess, "Popen", return_value=PopenFalso()):
            texto = media.reproducir(self.ctx, "rock")
        self.assertIn("la playlist Rock", texto)

    def test_archivo_por_nombre(self):
        self._crear("Rock/mi cancion.mp3")
        with mock.patch.object(media.subprocess, "Popen", return_value=PopenFalso()) as popen:
            texto = media.reproducir(self.ctx, "mi cancion")
        cmd = popen.call_args.args[0]
        self.assertTrue(any(c.endswith("mi cancion.mp3") for c in cmd))
        self.assertIn("«mi cancion»", texto)

    def test_sin_archivos_abre_youtube(self):
        with mock.patch.object(media.subprocess, "Popen", return_value=PopenFalso()) as popen:
            texto = media.reproducir(self.ctx, "luna de miel")
        cmd = popen.call_args.args[0]
        self.assertEqual(cmd[0], "xdg-open")
        self.assertIn("youtube.com/results", cmd[1])
        self.assertIn("luna", cmd[1])
        self.assertIn("abrí YouTube", texto)

    def test_falta_vlc_avisa(self):
        self._crear("Rock/a.mp3")
        with mock.patch.object(media.subprocess, "Popen", side_effect=FileNotFoundError):
            texto = media.reproducir(self.ctx, "rock")
        self.assertIn("No encontré VLC", texto)

    def test_pausa_sin_reproduccion(self):
        with mock.patch.object(media, "_playerctl", return_value=None):
            self.assertIn("No hay nada", media.pausar(self.ctx))
            self.assertIn("No hay nada", media.reanudar(self.ctx))

    def test_volumen_usa_pactl(self):
        with mock.patch.object(media.subprocess, "run", return_value=None) as run:
            texto = media.volumen(self.ctx, 10)
        self.assertIn("subido", texto)
        self.assertEqual(run.call_args.args[0][-1], "+10%")

    def test_buscar_sin_playerctl_avisa(self):
        with mock.patch.object(media, "_playerctl", return_value=None):
            self.assertIn("playerctl", media.buscar_segundos(self.ctx, 10))


if __name__ == "__main__":
    unittest.main()
