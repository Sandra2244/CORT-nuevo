"""Servidor HTTP local que sirve el HUD y su API."""

from __future__ import annotations

import json
import mimetypes
import shutil
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ESTATICOS = Path(__file__).parent / "static"


class _Handler(BaseHTTPRequestHandler):
    app = None
    server_version = "CORT-HUD/0.1"
    protocol_version = "HTTP/1.1"

    def log_message(self, formato, *args):  # noqa: A003
        return

    # --- utilidades -----------------------------------------------------
    def _json(self, datos: dict, codigo: int = 200) -> None:
        cuerpo = json.dumps(datos, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(cuerpo)

    def _archivo(self, ruta: str) -> None:
        rel = ruta.lstrip("/")
        destino = (ESTATICOS / rel).resolve()
        try:
            destino.relative_to(ESTATICOS.resolve())
        except ValueError:
            self._json({"error": "ruta no permitida"}, 403)
            return
        if destino.is_dir():
            destino = destino / "index.html"
        if not destino.is_file():
            self._json({"error": "no encontrado"}, 404)
            return
        datos = destino.read_bytes()
        if destino.suffix == ".webmanifest":
            tipo = "application/manifest+json"
        else:
            tipo = mimetypes.guess_type(str(destino))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", tipo + ("; charset=utf-8" if tipo.startswith("text/") or tipo.endswith("javascript") else ""))
        self.send_header("Content-Length", str(len(datos)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(datos)

    def _cuerpo(self) -> dict:
        try:
            largo = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            largo = 0
        if largo <= 0 or largo > 1_000_000:
            return {}
        try:
            return json.loads(self.rfile.read(largo).decode("utf-8"))
        except Exception:  # noqa: BLE001
            return {}

    # --- GET ------------------------------------------------------------
    def do_GET(self):  # noqa: N802
        ruta = urlparse(self.path).path
        if ruta in ("/", "/index.html"):
            self._archivo("index.html")
        elif ruta.startswith("/static/"):
            self._archivo(ruta[len("/static/"):])
        elif ruta == "/api/estado":
            self._json(self.app.estado_hud())
        elif ruta == "/api/modelos":
            self._json(self.app.listar_modelos())
        elif ruta == "/api/capacidades":
            self._json(self.app.capacidades())
        elif ruta == "/api/salud":
            self._json({"ok": True, "app": "CORT"})
        elif ruta == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
        else:
            self._json({"error": "no encontrado"}, 404)

    # --- POST -----------------------------------------------------------
    def do_POST(self):  # noqa: N802
        ruta = urlparse(self.path).path
        datos = self._cuerpo()
        if ruta == "/api/chat":
            texto = str(datos.get("texto", "")).strip()
            if not texto:
                self._json({"error": "texto vacío"}, 400)
                return
            try:
                self._json(self.app.responder(texto))
            except Exception as exc:  # noqa: BLE001
                self._json({"respuesta": f"El núcleo falló: {type(exc).__name__}", "herramienta": "error"}, 500)
            return
        if ruta == "/api/accion":
            accion = str(datos.get("accion", ""))
            if accion == "silencio":
                activar = bool(datos.get("activar", True))
                self.app.tts.callar(activar)
                self.app.bus.flag("silencio", activar)
                self._json({"ok": True, "silencio": activar})
            elif accion == "detener":
                self._json(self.app.detener_turno())
            elif accion == "escuchar":
                self._json(self.app.escuchar_una_vez())
            elif accion in ("pausa", "reanudar"):
                from ..tools import media

                texto = media.pausar(self.app.ctx) if accion == "pausa" else media.reanudar(self.app.ctx)
                self._json({"ok": True, "mensaje": texto})
            else:
                self._json({"error": f"acción desconocida: {accion}"}, 400)
            return
        if ruta == "/api/modelos/seleccionar":
            nombre = str(datos.get("nombre", "")).strip()
            self._json(self.app.seleccionar_modelo(nombre))
            return
        if ruta == "/api/modelos/descargar":
            nombre = str(datos.get("nombre", "")).strip()
            self._descargar_modelo(nombre)
            return
        if ruta == "/api/modelos/cancelar":
            self._json(self.app.cancelar_descarga())
            return
        self._json({"error": "no encontrado"}, 404)

    # --- descarga con progreso -----------------------------------------
    def _descargar_modelo(self, nombre: str) -> None:
        """Emite NDJSON con el avance de /api/pull; cierra la conexión al terminar."""
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True
        vivo = {"si": True}

        def emitir(dato: dict) -> None:
            if not vivo["si"]:
                return
            linea = json.dumps(dato, ensure_ascii=False) + "\n"
            try:
                self.wfile.write(linea.encode("utf-8"))
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, OSError):
                # El HUD se cerró: la descarga sigue y el avance queda en /api/estado.
                vivo["si"] = False

        try:
            emitir({"inicio": True, "modelo": nombre})
            resultado = self.app.descargar_modelo(nombre, al_progreso=emitir)
            if not resultado.get("ok"):
                emitir({"error": resultado.get("error", "la descarga falló")})
            else:
                emitir(
                    {
                        "ok": True,
                        "modelo": resultado.get("modelo", nombre),
                        "estado": resultado.get("estado", "completado"),
                        "activo": resultado.get("activo", ""),
                    }
                )
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as exc:  # noqa: BLE001
            emitir({"error": f"{type(exc).__name__}: {exc}"})


class Servidor:
    def __init__(self, app, host: str | None = None, puerto: int | None = None):
        self.app = app
        self.host = host or str(app.cfg.get("hud.host", "127.0.0.1"))
        self.puerto = int(app.cfg.get("hud.puerto", 8765) if puerto is None else puerto)
        self._httpd: ThreadingHTTPServer | None = None
        self._hilo: threading.Thread | None = None
        self.url = ""

    def iniciar(self) -> str:
        handler = type("HandlerCort", (_Handler,), {"app": self.app})
        ultimo_error = None
        for intento in range(10):
            try:
                self._httpd = ThreadingHTTPServer((self.host, self.puerto + intento), handler)
                self.puerto = self._httpd.server_address[1]
                break
            except OSError as exc:
                ultimo_error = exc
        if self._httpd is None:
            raise RuntimeError(f"No pude abrir el puerto del HUD: {ultimo_error}")
        self._httpd.daemon_threads = True
        self._hilo = threading.Thread(target=self._httpd.serve_forever, daemon=True, name="cort-hud")
        self._hilo.start()
        self.url = f"http://{self.host}:{self.puerto}/"
        self.app.bus.log(f"hud · {self.url}")
        return self.url

    def detener(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None


def abrir_hud(url: str, modo: str = "auto") -> bool:
    """Abre el HUD en ventana nativa o navegador. Devuelve True si bloquea."""
    modo = (modo or "auto").lower()
    if modo == "ninguno":
        print(f"CORT · HUD disponible en {url}")
        return False
    if modo in ("auto", "webview"):
        try:
            import webview  # type: ignore

            ventana = webview.create_window(
                "CORT",
                url,
                width=1280,
                height=820,
                background_color="#03060a",
                confirm_close=False,
            )
            webview.start()
            return True
        except Exception as exc:  # noqa: BLE001
            if modo == "webview":
                print(f"CORT · no pude abrir la ventana nativa: {type(exc).__name__}")
    if modo in ("auto", "navegador"):
        abierto = False
        try:
            abierto = webbrowser.open(url)
        except Exception:  # noqa: BLE001
            abierto = False
        if not abierto and shutil.which("xdg-open"):
            try:
                import subprocess

                subprocess.Popen(["xdg-open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                abierto = True
            except Exception:  # noqa: BLE001
                abierto = False
        if abierto:
            print(f"CORT · HUD abierto en {url}")
            return False
        print(f"CORT · no pude abrir una ventana. Abrí esta URL: {url}")
    return False
