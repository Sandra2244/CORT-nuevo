"""Servidor HTTP local que sirve el HUD y su API."""

from __future__ import annotations

import hmac
import json
import mimetypes
import shutil
import socket
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ESTATICOS = Path(__file__).parent / "static"

# Direcciones que son "este equipo". Un HUD abierto en 0.0.0.0 sigue siendo
# local para la PC: quien consulta desde 127.0.0.1 es el propio usuario.
LOCALES = ("127.", "::1", "::ffff:127.")

PAGINA_SIN_ACCESO = """<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CORT · falta el token</title>
<style>
body{{background:#04090f;color:#cfe9f5;font:14px/1.6 system-ui,sans-serif;
margin:0;padding:36px 22px}}
code{{background:#0b1a24;padding:2px 6px;border-radius:4px;color:#7fe7ff}}
p{{max-width:42em}}
</style></head><body>
<h1>CORT está protegido</h1>
<p>Este HUD está abierto a la red local, así que pide una llave. Copia el enlace
completo que imprime CORT en la PC —lleva <code>?token=…</code>— y ábrelo aquí.</p>
<p>En la PC: <code>python3 -m cort --hud --host 0.0.0.0 --token tu-llave</code></p>
</body></html>
"""


def es_local(ip: str) -> bool:
    """Si la conexión viene de esta misma máquina."""
    return ip.startswith(LOCALES)


def ruta_publica(ruta: str) -> bool:
    """Lo que se sirve sin llave: la ropa de la página y el latido.

    Sin CSS ni JS el HUD no puede ni pintarse el aviso de «falta el token», y
    `/api/salud` no dice nada que un desconocido pueda usar. Lo que manda y lo
    que responde exige el token.
    """
    return ruta.startswith("/static/") or ruta in ("/favicon.ico", "/api/salud")


class _Handler(BaseHTTPRequestHandler):
    app = None
    token = ""
    server_version = "CORT-HUD/0.1"
    protocol_version = "HTTP/1.1"

    def log_message(self, formato, *args):  # noqa: A003
        return

    # --- acceso ---------------------------------------------------------
    def _autorizado(self) -> bool:
        """Local siempre entra; desde la red sólo con el token del enlace."""
        ip = self.client_address[0] if self.client_address else ""
        if es_local(ip):
            return True
        if not self.token:
            return False
        dado = self.headers.get("X-CORT-Token", "")
        if not dado:
            dado = parse_qs(urlparse(self.path).query).get("token", [""])[0]
        if not dado:
            return False
        # En bytes: `compare_digest` con `str` rechaza cualquier tilde, y un
        # token con tildes es perfectamente escribible.
        return hmac.compare_digest(str(dado).encode("utf-8"), str(self.token).encode("utf-8"))

    def _sin_acceso(self) -> None:
        ruta = urlparse(self.path).path
        if ruta.startswith("/api/"):
            self._json({"error": "falta el token del HUD"}, 401)
            return
        cuerpo = PAGINA_SIN_ACCESO.encode("utf-8")
        self.send_response(401)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(cuerpo)

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
        # Los recursos de la página van sin llave: sin ellos el HUD no puede
        # ni pintarse. Lo que manda y lo que responde sí exige el token.
        if not ruta_publica(ruta) and not self._autorizado():
            self._sin_acceso()
            return
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
        if not self._autorizado():
            self._sin_acceso()
            return
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
        self.token = str(app.cfg.get("hud.token", "") or "")
        self._httpd: ThreadingHTTPServer | None = None
        self._hilo: threading.Thread | None = None
        self.url = ""
        self.url_red = ""

    @staticmethod
    def _es_bucle(direccion: str) -> bool:
        return direccion in ("127.0.0.1", "localhost", "::1", "")

    @staticmethod
    def ip_de_red() -> str:
        """IP con la que esta PC se ve desde la red. No manda ningún paquete."""
        try:
            zagu = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                zagu.connect(("8.8.8.8", 80))
                return str(zagu.getsockname()[0])
            finally:
                zagu.close()
        except OSError:
            return ""

    def url_para_red(self) -> str:
        """El enlace que hay que escribir (o pegar) en el teléfono."""
        direccion = self.ip_de_red() or (self.host if not self._es_bucle(self.host) else "")
        if not direccion:
            return ""
        cola = f"?token={self.token}" if self.token else ""
        return f"http://{direccion}:{self.puerto}/{cola}"

    def iniciar(self) -> str:
        if not self._es_bucle(self.host) and not self.token:
            raise RuntimeError(
                "El HUD está apuntando a la red ("
                f"{self.host}) sin `hud.token`: quedaría abierto a cualquiera "
                "con el mismo wifi. Escribe un token en config/cort.toml o pasa "
                "--token al arrancar."
            )
        handler = type("HandlerCort", (_Handler,), {"app": self.app, "token": self.token})
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
        # `0.0.0.0` no es una dirección donde nadie pueda escribir un navegador:
        # para la PC se muestra el bucle, y para el teléfono la IP real de la red.
        anfitrion = "127.0.0.1" if self.host in ("0.0.0.0", "::", "") else self.host
        self.url = f"http://{anfitrion}:{self.puerto}/"
        self.url_red = "" if self._es_bucle(self.host) else self.url_para_red()
        self.app.bus.log(f"hud · {self.url}")
        if self.url_red:
            self.app.bus.log(f"hud en la red · {self.url_red}")
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
