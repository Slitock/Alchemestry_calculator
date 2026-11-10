"""Подключение к SQLite.

Файл базы: data/alchemy.db (переопределяется переменной ALCHEMY_DB).
Соединение живёт один HTTP-запрос: sqlite3 не умеет безопасно шарить
одно соединение между потоками, а Flask по умолчанию многопоточный.
"""

import os
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

DB_PATH = Path(
    os.environ.get("ALCHEMY_DB") or (BASE_DIR / "data" / "alchemy.db")
).expanduser()


def connect(path=None):
    """Новое соединение с включёнными внешними ключами и WAL."""
    target = Path(path or DB_PATH)
    target.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_schema(conn):
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()


def get_db():
    """Соединение текущего запроса (кладут в flask.g)."""
    from flask import g

    if "db" not in g:
        g.db = connect()
    return g.db


def close_db(_exception=None):
    from flask import g

    conn = g.pop("db", None)
    if conn is not None:
        conn.close()
