"""Voz de CORT con espeak-ng en un hilo propio."""

from __future__ import annotations

import queue
import re
import shutil
import subprocess
import threading

from ..text import recortar

_RE_URL = re.compile(r"https?://\S+")
_RE_MARKDOWN = re.compile(r"[*_`#>]+")


def _limpiar(texto: str) -> str:
    texto = _RE_URL.sub(" ", texto)
    texto = _RE_MARKDOWN.sub(" ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return recortar(texto, 600)


class Tts:
    def __init__(self, cfg, bus=None):
        self.bus = bus
        self.motor = str(cfg.get("voz.motor", "espeak-ng"))
        self.binario = shutil.which(self.motor)
        self.voz = str(cfg.get("voz.voz", "es-mx+f3"))
        self.velocidad = int(cfg.get("voz.velocidad", 165))
        self.tono = int(cfg.get("voz.tono", 52))
        self.activo = bool(cfg.get("voz.tts", True) and self.binario)
        self.silencio = False
        self._cola: queue.Queue[str] = queue.Queue()
        self._proc = None
        self._lock = threading.RLock()
        self._hilo = threading.Thread(target=self._worker, daemon=True, name="cort-tts")
        self._hilo.start()

    @property
    def disponible(self) -> bool:
        return bool(self.binario)

    def hablar(self, texto: str) -> None:
        if not self.activo or self.silencio:
            return
        limpio = _limpiar(texto)
        if limpio:
            self._cola.put(limpio)

    def callar(self, activar: bool = True) -> None:
        self.silencio = bool(activar)
        if self.silencio:
            self.detener()

    def detener(self) -> None:
        with self._lock:
            if self._proc is not None and self._proc.poll() is None:
                try:
                    self._proc.terminate()
                except Exception:  # noqa: BLE001
                    pass
            try:
                while True:
                    self._cola.get_nowait()
            except queue.Empty:
                pass
        if self.bus is not None:
            self.bus.estado("idle")

    def _worker(self) -> None:
        while True:
            texto = self._cola.get()
            if texto is None:
                return
            with self._lock:
                if self.silencio:
                    continue
                cmd = [
                    self.binario,
                    "-v", self.voz,
                    "-s", str(self.velocidad),
                    "-p", str(self.tono),
                    texto,
                ]
                try:
                    if self.bus is not None:
                        self.bus.estado("speaking")
                    self._proc = subprocess.Popen(
                        cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                    self._proc.wait()
                except Exception:  # noqa: BLE001
                    pass
                finally:
                    self._proc = None
            if self._cola.empty() and self.bus is not None:
                self.bus.estado("idle")
