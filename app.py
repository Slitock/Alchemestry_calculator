"""Веб-версия алхимического калькулятора.

Ноутбук выступает локальным хостингом: сервер слушает 0.0.0.0, остальные
устройства в той же сети открывают страницу по IP ноутбука.

Данные ингредиентов живут в SQLite (data/alchemy.db), редактируются через
/admin. Запуск: .venv/bin/python app.py
"""

import os
import secrets
import socket
from collections import Counter
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_from_directory

from core.mixed import Mixed
from database import db, repository, seed
from database.omnisention_info import OMNISENTION_GRADUET

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"

MAX_COUNT = 99  # больше одного ингредиента за раз в котёл не кладём

app = Flask(
    __name__,
    static_folder=str(WEB_DIR / "static"),
    static_url_path="/static",
)

app.teardown_appcontext(db.close_db)

GRADATION = [
    {"effects": count, "min": bounds[0], "max": bounds[1]}
    for count, bounds in OMNISENTION_GRADUET.items()
]

_db_ready = False


def ensure_database_ready():
    """Схема и сид при первом запросе (идемпотентно, дёшево после первого раза)."""
    global _db_ready
    if not _db_ready:
        seed.ensure_database()
        _db_ready = True


@app.before_request
def prepare_database():
    ensure_database_ready()


@app.before_request
def protect_admin():
    """Пароль включается переменной ALCHEMY_ADMIN_PASSWORD.

    Без неё админка открыта всем в локальной сети — для домашней игры это
    осознанный выбор, но не для публичной сети.
    """
    if not request.path.startswith(("/admin", "/api/admin")):
        return None

    password = os.environ.get("ALCHEMY_ADMIN_PASSWORD")
    if not password:
        return None

    auth = request.authorization
    expected_user = os.environ.get("ALCHEMY_ADMIN_USER", "admin")
    if (
        auth is not None
        and secrets.compare_digest(auth.username or "", expected_user)
        and secrets.compare_digest(auth.password or "", password)
    ):
        return None

    return Response(
        "Требуется авторизация администратора.",
        401,
        {"WWW-Authenticate": 'Basic realm="alchemy"'},
    )


def parse_cauldron(payload, available):
    """Проверяет тело запроса и возвращает список Ingridient либо текст ошибки."""
    items = payload.get("ingredients")
    if not isinstance(items, list):
        return None, "Поле 'ingredients' должно быть списком."

    cauldron = []
    for item in items:
        if not isinstance(item, dict):
            return None, "Каждый ингредиент должен быть объектом {name, count}."

        name = item.get("name")
        if name not in available:
            return None, f"Неизвестный ингредиент: {name!r}"

        count = item.get("count", 1)
        # bool — подкласс int, поэтому отсекаем его отдельно
        if isinstance(count, bool) or not isinstance(count, int):
            return None, "Количество должно быть целым числом."
        if not 1 <= count <= MAX_COUNT:
            return None, f"Количество должно быть от 1 до {MAX_COUNT}."

        cauldron.extend([available[name]] * count)

    if not cauldron:
        return None, "Котёл пуст — не из чего варить."

    return cauldron, None


# ---------- Страницы ----------


@app.get("/")
def index():
    return send_from_directory(WEB_DIR, "index.html")


@app.get("/admin")
def admin_page():
    return send_from_directory(WEB_DIR, "admin.html")


# ---------- Публичный API ----------


@app.get("/api/ingredients")
def api_ingredients():
    return jsonify({"ingredients": repository.list_ingredients(db.get_db())})


@app.get("/api/rules")
def api_rules():
    conn = db.get_db()
    return jsonify(
        {
            "conflicts": repository.list_conflict_pairs(conn),
            "gradation": GRADATION,
            "max_count": MAX_COUNT,
        }
    )


@app.post("/api/brew")
def api_brew():
    conn = db.get_db()
    cauldron, error = parse_cauldron(
        request.get_json(silent=True) or {}, repository.ingredients_by_name(conn)
    )
    if error:
        return jsonify({"error": error}), 400

    potion = Mixed(cauldron, antagonists=repository.get_antagonists(conn))

    # Группируем одинаковые эффекты: ("урон", "урон") -> {"урон": 2}
    effects = [
        {"name": name, "count": count}
        for name, count in Counter(potion.properties).most_common()
    ]
    removed = [
        {"effect": pair[0], "antieffect": pair[1], "count": count}
        for pair, count in Counter(potion.removed_conflicts).most_common()
    ]

    return jsonify(
        {
            "recept": potion.recept,
            "properties": potion.properties,
            "effects": effects,
            "omnisention": potion.omnisention,
            "raw_omnisention": potion.raw_omnisention,
            "crystals": potion.crystals,
            "removed": removed,
        }
    )


# ---------- Админка ----------


@app.get("/api/admin/data")
def admin_data():
    """Всё, что нужно админке, одним запросом."""
    conn = db.get_db()
    return jsonify(
        {
            "ingredients": repository.list_ingredients(conn),
            "effects": repository.list_effects(conn),
            "antagonists": repository.list_conflict_pairs(conn),
        }
    )


@app.post("/api/admin/ingredients")
def admin_create_ingredient():
    created = repository.create_ingredient(
        db.get_db(), request.get_json(silent=True) or {}
    )
    return jsonify({"ingredient": created}), 201


@app.put("/api/admin/ingredients/<int:ingredient_id>")
def admin_update_ingredient(ingredient_id):
    updated = repository.update_ingredient(
        db.get_db(), ingredient_id, request.get_json(silent=True) or {}
    )
    return jsonify({"ingredient": updated})


@app.delete("/api/admin/ingredients/<int:ingredient_id>")
def admin_delete_ingredient(ingredient_id):
    repository.delete_ingredient(db.get_db(), ingredient_id)
    return jsonify({"deleted": ingredient_id})


@app.post("/api/admin/effects")
def admin_create_effect():
    name = repository.add_effect(
        db.get_db(), (request.get_json(silent=True) or {}).get("name")
    )
    return jsonify({"effect": name}), 201


@app.post("/api/admin/antagonists")
def admin_create_antagonist():
    payload = request.get_json(silent=True) or {}
    pair = repository.add_antagonist(
        db.get_db(), payload.get("effect"), payload.get("antieffect")
    )
    return jsonify({"pair": pair}), 201


@app.delete("/api/admin/antagonists")
def admin_delete_antagonist():
    repository.delete_antagonist(
        db.get_db(), request.args.get("effect"), request.args.get("antieffect")
    )
    return jsonify({"deleted": True})


# ---------- Ошибки ----------


@app.errorhandler(repository.ValidationError)
def handle_validation(error):
    return jsonify({"error": str(error)}), 400


@app.errorhandler(repository.NotFound)
def handle_not_found(error):
    return jsonify({"error": str(error)}), 404


@app.errorhandler(404)
def not_found(_error):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Страница не найдена."}), 404
    return "Страница не найдена.", 404


def local_addresses():
    """Все IPv4-адреса машины, кроме loopback.

    UDP-соединение ничего не отправляет, но заставляет ядро выбрать интерфейс
    по умолчанию — его адрес обычно и нужен. Остальные адреса добавляем из
    резолва имени хоста: на ноутбуке их бывает несколько (Wi-Fi, docker, VPN).
    """
    found = []

    def add(address):
        if address and not address.startswith("127.") and address not in found:
            found.append(address)

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("10.255.255.255", 1))
            add(sock.getsockname()[0])
    except OSError:
        pass

    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            add(info[4][0])
    except OSError:
        pass

    # 172.16.0.0/12 — типичный диапазон docker-мостов, показываем их последними
    def score(address):
        if address.startswith("192.168."):
            return 0
        if address.startswith("10."):
            return 1
        if address.startswith("172."):
            return 3
        return 2

    return sorted(found, key=score)


def main():
    port = int(os.environ.get("ALCHEMY_PORT", "8000"))
    addresses = local_addresses()
    ensure_database_ready()

    print("=== Алхимический котёл: сервер запущен ===")
    print(f"  На этом ноутбуке:  http://127.0.0.1:{port}")
    if addresses:
        print(f"  В локальной сети:  http://{addresses[0]}:{port}")
        for extra in addresses[1:]:
            print(f"  ещё адрес:         http://{extra}:{port}")
    print(f"  Админка:           http://127.0.0.1:{port}/admin")
    print(f"  База данных:       {db.DB_PATH}")
    print("  Остановка: Ctrl+C")

    app.run(host="0.0.0.0", port=port, debug=os.environ.get("ALCHEMY_DEBUG") == "1")


if __name__ == "__main__":
    main()
