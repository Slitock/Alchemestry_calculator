"""Первичное наполнение базы из старых Python-справочников.

Источник сида — database/ingridients.py (INGREDIENTS) и database/test_bd.py
(PROPERTIES). После первого запуска данные живут в SQLite, и редактировать
их нужно через /admin, а не в этих файлах.

    python -m database.seed            # создать базу, если её нет
    python -m database.seed --force    # пересоздать и залить заново
"""

import sys

from database import db
from database.ingridients import INGREDIENTS
from database.test_bd import PROPERTIES


class EffectCache:
    """Имя эффекта -> id, чтобы не делать SELECT на каждый эффект."""

    def __init__(self, conn):
        self.conn = conn
        self.cache = {}

    def get(self, name):
        name = name.strip()
        if not name:
            raise ValueError("Пустое название эффекта.")

        if name not in self.cache:
            self.conn.execute("INSERT OR IGNORE INTO effect (name) VALUES (?)", (name,))
            row = self.conn.execute(
                "SELECT id FROM effect WHERE name = ?", (name,)
            ).fetchone()
            self.cache[name] = row["id"]

        return self.cache[name]


def seed_from_python(conn):
    """Заливает ингредиенты, эффекты и пары антагонистов."""
    effects = EffectCache(conn)

    for effect, antieffect in PROPERTIES.items():
        first = effects.get(effect)
        second = effects.get(antieffect)
        if first == second:
            continue
        # канонический порядок: в таблице пара хранится один раз
        low, high = sorted((first, second))
        conn.execute(
            "INSERT OR IGNORE INTO antagonist (effect_id, antieffect_id) VALUES (?, ?)",
            (low, high),
        )

    for name, info in INGREDIENTS.items():
        cursor = conn.execute(
            "INSERT INTO ingredient (name, omnisention, rareness) VALUES (?, ?, ?)",
            (name, int(info["omnisention"]), info["rareness"]),
        )
        ingredient_id = cursor.lastrowid

        for position, effect_name in enumerate(info["properties"]):
            conn.execute(
                "INSERT INTO ingredient_effect (ingredient_id, position, effect_id)"
                " VALUES (?, ?, ?)",
                (ingredient_id, position, effects.get(effect_name)),
            )

    conn.commit()


def is_empty(conn):
    return conn.execute("SELECT COUNT(*) FROM ingredient").fetchone()[0] == 0


def seed_if_empty(conn):
    """Возвращает True, если база была пустой и её наполнили."""
    if not is_empty(conn):
        return False
    seed_from_python(conn)
    return True


def reset(conn):
    """Удаляет всё содержимое, сохраняя схему."""
    conn.executescript(
        """
        DELETE FROM ingredient_effect;
        DELETE FROM ingredient;
        DELETE FROM antagonist;
        DELETE FROM effect;
        DELETE FROM sqlite_sequence
            WHERE name IN ('effect', 'ingredient');
        """
    )
    conn.commit()


def ensure_database(path=None):
    """Создаёт схему и наполняет базу, если она пустая. Идемпотентно."""
    conn = db.connect(path)
    try:
        db.init_schema(conn)
        return seed_if_empty(conn)
    finally:
        conn.close()


def main(argv):
    force = "--force" in argv

    conn = db.connect()
    try:
        db.init_schema(conn)
        if force:
            reset(conn)
        if is_empty(conn):
            seed_from_python(conn)
            print(f"База наполнена: {db.DB_PATH}")
        else:
            print(f"В базе уже есть данные: {db.DB_PATH} (--force для перезаписи)")
        counts = conn.execute(
            "SELECT (SELECT COUNT(*) FROM ingredient) AS ingredients,"
            "       (SELECT COUNT(*) FROM effect) AS effects,"
            "       (SELECT COUNT(*) FROM antagonist) AS antagonists"
        ).fetchone()
        print(
            f"Ингредиентов: {counts['ingredients']}, "
            f"эффектов: {counts['effects']}, "
            f"пар антагонистов: {counts['antagonists']}"
        )
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
