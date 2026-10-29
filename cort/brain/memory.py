"""Memoria persistente de CORT en SQLite: hechos, episodios y alarmas."""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime
from pathlib import Path

ESQUEMA = """
CREATE TABLE IF NOT EXISTS facts (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL,
    origen TEXT DEFAULT 'usuario',
    confianza REAL DEFAULT 1.0,
    creado TEXT NOT NULL,
    actualizado TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rol TEXT NOT NULL,
    texto TEXT NOT NULL,
    creado TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS alarms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cuando TEXT NOT NULL,
    texto TEXT NOT NULL,
    playlist TEXT DEFAULT '',
    disparada INTEGER DEFAULT 0,
    creada TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS meta (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_episodes_id ON episodes(id DESC);
CREATE INDEX IF NOT EXISTS idx_alarms_cuando ON alarms(cuando);
"""


def _ahora() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


class Memoria:
    def __init__(self, ruta: str | Path):
        self.ruta = Path(ruta)
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._db = sqlite3.connect(self.ruta, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        with self._lock:
            self._db.executescript(ESQUEMA)
            self._db.commit()

    # --- hechos ---------------------------------------------------------
    def recordar(self, clave: str, valor: str, origen: str = "usuario", confianza: float = 1.0) -> None:
        clave = " ".join(str(clave).lower().split())
        valor = " ".join(str(valor).split())
        if not clave or not valor:
            return
        ahora = _ahora()
        with self._lock:
            self._db.execute(
                """INSERT INTO facts (clave, valor, origen, confianza, creado, actualizado)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(clave) DO UPDATE SET
                     valor=excluded.valor, origen=excluded.origen,
                     confianza=excluded.confianza, actualizado=excluded.actualizado""",
                (clave, valor, origen, float(confianza), ahora, ahora),
            )
            self._db.commit()

    def hecho(self, clave: str) -> str | None:
        clave = " ".join(str(clave).lower().split())
        with self._lock:
            fila = self._db.execute("SELECT valor FROM facts WHERE clave = ?", (clave,)).fetchone()
        return fila["valor"] if fila else None

    def olvidar(self, clave: str) -> int:
        clave = " ".join(str(clave).lower().split())
        with self._lock:
            cur = self._db.execute(
                "DELETE FROM facts WHERE clave = ? OR clave LIKE ?", (clave, f"%{clave}%")
            )
            self._db.commit()
        return cur.rowcount

    def hechos(self, limite: int = 20) -> list[dict]:
        with self._lock:
            filas = self._db.execute(
                "SELECT clave, valor FROM facts ORDER BY actualizado DESC LIMIT ?", (limite,)
            ).fetchall()
        return [{"clave": f["clave"], "valor": f["valor"]} for f in filas]

    # --- episodios ------------------------------------------------------
    def agregar_episodio(self, rol: str, texto: str) -> None:
        with self._lock:
            self._db.execute(
                "INSERT INTO episodes (rol, texto, creado) VALUES (?, ?, ?)",
                (rol, texto, _ahora()),
            )
            # Podar sólo al pasarse del límite: en cada mensaje sería trabajo inútil.
            total = self._db.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
            if total > 500:
                self._db.execute(
                    "DELETE FROM episodes WHERE id NOT IN "
                    "(SELECT id FROM episodes ORDER BY id DESC LIMIT 500)"
                )
            self._db.commit()

    def episodios(self, limite: int = 8) -> list[dict]:
        with self._lock:
            filas = self._db.execute(
                "SELECT rol, texto FROM episodes ORDER BY id DESC LIMIT ?", (limite,)
            ).fetchall()
        return [{"rol": f["rol"], "texto": f["texto"]} for f in reversed(filas)]

    # --- alarmas --------------------------------------------------------
    def crear_alarma(self, cuando: datetime, texto: str, playlist: str = "") -> int:
        with self._lock:
            cur = self._db.execute(
                "INSERT INTO alarms (cuando, texto, playlist, creada) VALUES (?, ?, ?, ?)",
                (cuando.replace(microsecond=0).isoformat(), texto.strip() or "Es hora", playlist, _ahora()),
            )
            self._db.commit()
        return int(cur.lastrowid)

    def alarmas_pendientes(self, momento: datetime | None = None) -> list[dict]:
        momento = (momento or datetime.now()).replace(microsecond=0)
        with self._lock:
            filas = self._db.execute(
                "SELECT * FROM alarms WHERE disparada = 0 AND cuando <= ? ORDER BY cuando",
                (momento.isoformat(),),
            ).fetchall()
        return [dict(f) for f in filas]

    def proximas_alarmas(self, limite: int = 5) -> list[dict]:
        with self._lock:
            filas = self._db.execute(
                "SELECT * FROM alarms WHERE disparada = 0 ORDER BY cuando LIMIT ?", (limite,)
            ).fetchall()
        return [dict(f) for f in filas]

    def marcar_alarma(self, alarma_id: int) -> None:
        with self._lock:
            self._db.execute("UPDATE alarms SET disparada = 1 WHERE id = ?", (alarma_id,))
            self._db.commit()

    # --- meta -----------------------------------------------------------
    def meta(self, clave: str, valor: str | None = None) -> str | None:
        with self._lock:
            if valor is None:
                fila = self._db.execute("SELECT valor FROM meta WHERE clave = ?", (clave,)).fetchone()
                return fila["valor"] if fila else None
            self._db.execute(
                "INSERT INTO meta (clave, valor) VALUES (?, ?) "
                "ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor",
                (clave, valor),
            )
            self._db.commit()
        return valor

    def cerrar(self) -> None:
        with self._lock:
            self._db.close()
