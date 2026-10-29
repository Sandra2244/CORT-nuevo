"""Escucha con Vosk español y `arecord`. Todo es opcional: sin Vosk, no hay micrófono."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
from array import array
from pathlib import Path

from ..text import normalizar


def _rms(chunk: bytes) -> float:
    if not chunk:
        return 0.0
    muestras = array("h")
    muestras.frombytes(chunk)
    if not muestras:
        return 0.0
    suma = sum(s * s for s in muestras) / len(muestras)
    return suma ** 0.5


class Stt:
    def __init__(self, cfg, bus=None):
        self.cfg = cfg
        self.bus = bus
        self.activo = False
        self.modelo = None
        self.motivo = ""
        self._arecord = shutil.which("arecord")
        if not cfg.get("voz.stt", True):
            self.motivo = "desactivado en la configuración"
            return
        if not self._arecord:
            self.motivo = "falta arecord"
            return
        try:
            import vosk  # type: ignore
        except Exception:  # noqa: BLE001
            self.motivo = "falta el paquete vosk"
            return
        ruta = str(cfg.get("voz.modelo_vosk", "") or "")
        if not ruta:
            ruta = str(Path(cfg.datos_dir) / "vosk-es")
        if not Path(ruta).is_dir():
            self.motivo = f"falta el modelo de Vosk en {ruta}"
            return
        try:
            vosk.SetLogLevel(-1)
            self.modelo = vosk.Model(ruta)
            self._vosk = vosk
            self.vosk_dir = ruta
            self.activo = True
        except Exception as exc:  # noqa: BLE001
            self.motivo = f"no pude cargar el modelo: {type(exc).__name__}"

    @property
    def disponible(self) -> bool:
        return bool(self.activo and self.modelo is not None)

    def escuchar(self, max_s: float = 9.0, silencio_s: float = 1.0) -> str:
        if not self.disponible:
            return ""
        try:
            proc = subprocess.Popen(
                ["arecord", "-q", "-f", "S16_LE", "-r", "16000", "-c", "1", "-t", "raw"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
        except Exception:  # noqa: BLE001
            return ""
        rec = self._vosk.KaldiRecognizer(self.modelo, 16000)
        rec.SetWords(False)
        chunks = int(16000 * 2 * 0.25)
        hablado = False
        silencio = 0.0
        total = 0.0
        ultimo = ""
        if self.bus is not None:
            self.bus.estado("listening")
        try:
            while total < max_s:
                datos = proc.stdout.read(chunks) if proc.stdout else b""
                if not datos:
                    break
                total += 0.25
                nivel = _rms(datos)
                if nivel > 550:
                    hablado = True
                    silencio = 0.0
                elif hablado:
                    silencio += 0.25
                if rec.AcceptWaveform(datos):
                    texto = json.loads(rec.Result()).get("text", "").strip()
                    if texto:
                        ultimo = texto
                if hablado and silencio >= silencio_s:
                    break
        finally:
            try:
                proc.terminate()
            except Exception:  # noqa: BLE001
                pass
            if self.bus is not None:
                self.bus.estado("idle")
        if not ultimo:
            try:
                ultimo = json.loads(rec.FinalResult()).get("text", "").strip()
            except Exception:  # noqa: BLE001
                ultimo = ""
        return ultimo

    def escuchar_palabra(self, claves: list[str], max_s: float = 12.0) -> tuple[str, str]:
        """Devuelve (clave_detectada, resto_de_frase)."""
        texto = self.escuchar(max_s=max_s)
        norm = normalizar(texto)
        for clave in claves:
            pos = norm.find(clave)
            if pos >= 0:
                return clave, norm[pos + len(clave):].strip(" ,.")
        return "", norm
