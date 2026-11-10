"""Все обращения к базе: чтение каталога и CRUD из админки.

Здесь же валидация: именно она не даёт сохранить ингредиент с опечаткой
в названии эффекта — такого эффекта просто нет в справочнике.
"""

from core.ingredient import Ingridient

RARITIES = ("E", "D", "C", "B", "A", "S")
MAX_EFFECTS_PER_INGREDIENT = 12
MAX_NAME_LENGTH = 80
MAX_EFFECT_NAME_LENGTH = 60
OMNISENTION_MIN = -999
OMNISENTION_MAX = 999


class ValidationError(ValueError):
    """Данные от пользователя не прошли проверку (HTTP 400)."""


class NotFound(LookupError):
    """Запись не найдена (HTTP 404)."""


# ---------- Чтение ----------

_INGREDIENTS_SQL = """
    SELECT i.id, i.name, i.omnisention, i.rareness, e.name AS effect
    FROM ingredient AS i
    LEFT JOIN ingredient_effect AS ie ON ie.ingredient_id = i.id
    LEFT JOIN effect AS e ON e.id = ie.effect_id
    ORDER BY i.id, ie.position
"""


def list_ingredients(conn):
    """Полный каталог в том виде, в каком его ждёт фронтенд."""
    rows = conn.execute(_INGREDIENTS_SQL).fetchall()

    items = {}
    order = []
    for row in rows:
        item = items.get(row["id"])
        if item is None:
            item = {
                "id": row["id"],
                "name": row["name"],
                "omnisention": row["omnisention"],
                "rareness": row["rareness"],
                "properties": [],
            }
            items[row["id"]] = item
            order.append(row["id"])
        if row["effect"] is not None:
            item["properties"].append(row["effect"])

    return [items[ingredient_id] for ingredient_id in order]


def ingredient_payload(conn, ingredient_id):
    """Один ингредиент по id."""
    row = conn.execute(
        "SELECT id, name, omnisention, rareness FROM ingredient WHERE id = ?",
        (ingredient_id,),
    ).fetchone()
    if row is None:
        raise NotFound("Ингредиент не найден.")

    effects = [
        effect["name"]
        for effect in conn.execute(
            """
            SELECT e.name
            FROM ingredient_effect AS ie
            JOIN effect AS e ON e.id = ie.effect_id
            WHERE ie.ingredient_id = ?
            ORDER BY ie.position
            """,
            (ingredient_id,),
        )
    ]

    return {
        "id": row["id"],
        "name": row["name"],
        "omnisention": row["omnisention"],
        "rareness": row["rareness"],
        "properties": effects,
    }


def ingredients_by_name(conn):
    """Словарь имя -> Ingridient для расчёта варки."""
    result = {}
    for item in list_ingredients(conn):
        result[item["name"]] = Ingridient(
            name=item["name"],
            omnisention=item["omnisention"],
            properties=item["properties"],
            rareness=item["rareness"],
        )
    return result


def list_effects(conn):
    names = [row["name"] for row in conn.execute("SELECT name FROM effect")]
    # SQLite COLLATE NOCASE умеет только ASCII, кириллицу сортируем в Python
    return sorted(names, key=str.casefold)


def find_by_name(conn, table, name):
    """Поиск по имени без учёта регистра.

    SQLite-овский COLLATE NOCASE сравнивает только латиницу, поэтому
    «Черная роза» и «черная роза» для него разные строки. Сравниваем в Python.
    Таблицы маленькие (десятки строк), так что это дёшево.
    """
    needle = str(name or "").strip().casefold()
    if not needle:
        return None

    for row in conn.execute(f"SELECT id, name FROM {table}"):
        if row["name"].casefold() == needle:
            return row
    return None


def list_conflict_pairs(conn):
    """Пары антагонистов в каноническом виде (каждая — один раз)."""
    rows = conn.execute(
        """
        SELECT first.name AS effect, second.name AS antieffect
        FROM antagonist AS a
        JOIN effect AS first ON first.id = a.effect_id
        JOIN effect AS second ON second.id = a.antieffect_id
        ORDER BY a.effect_id, a.antieffect_id
        """
    ).fetchall()
    return [{"effect": row["effect"], "antieffect": row["antieffect"]} for row in rows]


def get_antagonists(conn):
    """Симметричный словарь эффект -> антагонист для core.mixed.Mixed."""
    mapping = {}
    for pair in list_conflict_pairs(conn):
        mapping[pair["effect"]] = pair["antieffect"]
        mapping[pair["antieffect"]] = pair["effect"]
    return mapping


# ---------- Проверка данных ----------

def _clean_effects(conn, raw_effects):
    if not isinstance(raw_effects, list):
        raise ValidationError("Поле properties должно быть списком эффектов.")

    if len(raw_effects) > MAX_EFFECTS_PER_INGREDIENT:
        raise ValidationError(
            f"Не больше {MAX_EFFECTS_PER_INGREDIENT} эффектов на ингредиент."
        )

    # имена эффектов в базе канонические: сравниваем без учёта регистра,
    # сохраняем написание из справочника
    canonical = {
        row["name"].casefold(): row["name"]
        for row in conn.execute("SELECT name FROM effect")
    }

    cleaned = []
    unknown = []
    for effect in raw_effects:
        if not isinstance(effect, str) or not effect.strip():
            raise ValidationError("Каждый эффект должен быть непустой строкой.")

        resolved = canonical.get(effect.strip().casefold())
        if resolved is None:
            unknown.append(effect.strip())
        else:
            cleaned.append(resolved)

    if unknown:
        names = ", ".join(sorted(set(unknown)))
        raise ValidationError(
            f"Неизвестные эффекты: {names}. Сначала добавьте их в справочник."
        )

    return cleaned


def _validate_payload(conn, payload, ingredient_id=None):
    if not isinstance(payload, dict):
        raise ValidationError("Ожидался JSON-объект.")

    name = str(payload.get("name") or "").strip()
    if not name:
        raise ValidationError("Название не может быть пустым.")
    if len(name) > MAX_NAME_LENGTH:
        raise ValidationError(f"Название длиннее {MAX_NAME_LENGTH} символов.")

    try:
        omnisention = int(payload.get("omnisention"))
    except (TypeError, ValueError):
        raise ValidationError("Омнисенция должна быть целым числом.") from None
    if not OMNISENTION_MIN <= omnisention <= OMNISENTION_MAX:
        raise ValidationError(
            f"Омнисенция должна быть от {OMNISENTION_MIN} до {OMNISENTION_MAX}."
        )

    rareness = str(payload.get("rareness") or "").strip().upper()
    if rareness not in RARITIES:
        raise ValidationError("Редкость должна быть одной из: E, D, C, B, A, S.")

    effects = _clean_effects(conn, payload.get("properties", []))

    duplicate = find_by_name(conn, "ingredient", name)
    if duplicate is not None and duplicate["id"] != ingredient_id:
        raise ValidationError(f"Ингредиент «{name}» уже есть в базе.")

    return name, omnisention, rareness, effects


def _save_effects(conn, ingredient_id, effects):
    conn.execute(
        "DELETE FROM ingredient_effect WHERE ingredient_id = ?", (ingredient_id,)
    )
    for position, effect_name in enumerate(effects):
        conn.execute(
            """
            INSERT INTO ingredient_effect (ingredient_id, position, effect_id)
            SELECT ?, ?, id FROM effect WHERE name = ?
            """,
            (ingredient_id, position, effect_name),
        )


# ---------- Запись ----------

def create_ingredient(conn, payload):
    name, omnisention, rareness, effects = _validate_payload(conn, payload)

    cursor = conn.execute(
        "INSERT INTO ingredient (name, omnisention, rareness) VALUES (?, ?, ?)",
        (name, omnisention, rareness),
    )
    ingredient_id = cursor.lastrowid
    _save_effects(conn, ingredient_id, effects)
    conn.commit()

    return ingredient_payload(conn, ingredient_id)


def update_ingredient(conn, ingredient_id, payload):
    exists = conn.execute(
        "SELECT 1 FROM ingredient WHERE id = ?", (ingredient_id,)
    ).fetchone()
    if exists is None:
        raise NotFound("Ингредиент не найден.")

    name, omnisention, rareness, effects = _validate_payload(
        conn, payload, ingredient_id=ingredient_id
    )

    conn.execute(
        "UPDATE ingredient SET name = ?, omnisention = ?, rareness = ? WHERE id = ?",
        (name, omnisention, rareness, ingredient_id),
    )
    _save_effects(conn, ingredient_id, effects)
    conn.commit()

    return ingredient_payload(conn, ingredient_id)


def delete_ingredient(conn, ingredient_id):
    cursor = conn.execute("DELETE FROM ingredient WHERE id = ?", (ingredient_id,))
    conn.commit()
    if cursor.rowcount == 0:
        raise NotFound("Ингредиент не найден.")


def add_effect(conn, name):
    name = str(name or "").strip()
    if not name:
        raise ValidationError("Название эффекта не может быть пустым.")
    if len(name) > MAX_EFFECT_NAME_LENGTH:
        raise ValidationError(
            f"Название эффекта длиннее {MAX_EFFECT_NAME_LENGTH} символов."
        )

    existing = find_by_name(conn, "effect", name)
    if existing is not None:
        raise ValidationError(f"Эффект «{existing['name']}» уже есть в справочнике.")

    conn.execute("INSERT INTO effect (name) VALUES (?)", (name,))
    conn.commit()
    return name


def _effect_ref(conn, name):
    row = find_by_name(conn, "effect", name)
    if row is None:
        raise ValidationError(f"Неизвестный эффект: {name!r}")
    return row["id"], row["name"]


def add_antagonist(conn, effect, antieffect):
    first_id, first_name = _effect_ref(conn, effect)
    second_id, second_name = _effect_ref(conn, antieffect)

    if first_id == second_id:
        raise ValidationError("Эффект не может быть антагонистом сам себе.")

    low, high = sorted((first_id, second_id))
    names = {first_id: first_name, second_id: second_name}

    existing = conn.execute(
        "SELECT 1 FROM antagonist WHERE effect_id = ? AND antieffect_id = ?",
        (low, high),
    ).fetchone()
    if existing is not None:
        raise ValidationError("Такая пара уже есть.")

    conn.execute(
        "INSERT INTO antagonist (effect_id, antieffect_id) VALUES (?, ?)", (low, high)
    )
    conn.commit()

    return {"effect": names[low], "antieffect": names[high]}


def delete_antagonist(conn, effect, antieffect):
    first_id, _ = _effect_ref(conn, effect)
    second_id, _ = _effect_ref(conn, antieffect)

    if first_id == second_id:
        raise ValidationError("Пара должна состоять из двух разных эффектов.")

    low, high = sorted((first_id, second_id))
    cursor = conn.execute(
        "DELETE FROM antagonist WHERE effect_id = ? AND antieffect_id = ?", (low, high)
    )
    conn.commit()
    if cursor.rowcount == 0:
        raise NotFound("Такой пары нет.")
