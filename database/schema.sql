-- Схема алхимической базы.
-- Применяется при первом запуске (database/seed.py), вручную править не нужно.

PRAGMA foreign_keys = ON;

-- Эффекты: справочник. На него ссылаются ингредиенты, поэтому опечатка
-- в названии эффекта становится невозможной.
CREATE TABLE IF NOT EXISTS effect (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

-- Пары антагонистов. Пара хранится один раз в «каноническом» порядке
-- (effect_id < antieffect_id), симметричность восстанавливает репозиторий.
CREATE TABLE IF NOT EXISTS antagonist (
    effect_id     INTEGER NOT NULL REFERENCES effect(id) ON DELETE CASCADE,
    antieffect_id INTEGER NOT NULL REFERENCES effect(id) ON DELETE CASCADE,
    PRIMARY KEY (effect_id, antieffect_id),
    CHECK (effect_id < antieffect_id)
);

CREATE TABLE IF NOT EXISTS ingredient (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    omnisention INTEGER NOT NULL,
    rareness    TEXT NOT NULL CHECK (rareness IN ('E', 'D', 'C', 'B', 'A', 'S')),
    image       TEXT NOT NULL DEFAULT 'no img'
);

-- Состав ингредиента. position нужен, потому что дубли эффектов значимы:
-- «урон» дважды — это два эффекта, а не один.
CREATE TABLE IF NOT EXISTS ingredient_effect (
    ingredient_id INTEGER NOT NULL REFERENCES ingredient(id) ON DELETE CASCADE,
    position      INTEGER NOT NULL,
    effect_id     INTEGER NOT NULL REFERENCES effect(id) ON DELETE RESTRICT,
    PRIMARY KEY (ingredient_id, position)
);

CREATE INDEX IF NOT EXISTS idx_ingredient_effect_effect
    ON ingredient_effect (effect_id);
