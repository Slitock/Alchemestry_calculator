/* Админка: список ингредиентов, форма и справочник эффектов.
 * Вся проверка данных — на сервере (database/repository.py); здесь только
 * удобство: подсказки, черновик эффектов и понятные сообщения об ошибках.
 */

const state = {
  ingredients: [],
  effects: [],
  antagonists: [],
  editingId: null,
  draftEffects: [], // эффекты редактируемого ингредиента, дубли разрешены
  query: "",
  saving: false,
};

const el = {
  status: document.getElementById("db-state"),
  search: document.getElementById("search"),
  list: document.getElementById("ingredient-list"),
  listCount: document.getElementById("list-count"),
  newButton: document.getElementById("new-button"),

  form: document.getElementById("form"),
  title: document.getElementById("editor-title"),
  hint: document.getElementById("editor-hint"),
  name: document.getElementById("field-name"),
  omnisention: document.getElementById("field-omnisention"),
  rareness: document.getElementById("field-rareness"),
  chips: document.getElementById("effect-chips"),
  effectsCount: document.getElementById("effects-count"),
  effectSelect: document.getElementById("effect-select"),
  effectAdd: document.getElementById("effect-add"),
  saveButton: document.getElementById("save-button"),
  resetButton: document.getElementById("reset-button"),
  deleteButton: document.getElementById("delete-button"),
  errors: document.getElementById("form-errors"),

  pairs: document.getElementById("pairs"),
  pairA: document.getElementById("pair-a"),
  pairB: document.getElementById("pair-b"),
  pairAdd: document.getElementById("pair-add"),
  newEffect: document.getElementById("new-effect"),
  newEffectAdd: document.getElementById("new-effect-add"),

  toast: document.getElementById("toast"),
};

/* ---------- Утилиты ---------- */

let toastTimer = null;

function toast(message, ok = false) {
  el.toast.textContent = message;
  el.toast.classList.toggle("toast--ok", ok);
  el.toast.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    el.toast.hidden = true;
  }, 4000);
}

function showErrors(messages) {
  const list = Array.isArray(messages) ? messages : [messages];
  el.errors.replaceChildren(
    ...list.map((message) => {
      const item = document.createElement("li");
      item.textContent = message;
      return item;
    })
  );
  el.errors.hidden = false;
}

function clearErrors() {
  el.errors.hidden = true;
  el.errors.replaceChildren();
}

async function fetchJSON(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  let data = {};
  try {
    data = await response.json();
  } catch {
    data = {};
  }

  if (!response.ok) {
    throw new Error(data.error || `Сервер ответил ${response.status}`);
  }
  return data;
}

function aggregate(list) {
  const order = [];
  const counts = new Map();
  for (const value of list) {
    if (!counts.has(value)) {
      counts.set(value, 0);
      order.push(value);
    }
    counts.set(value, counts.get(value) + 1);
  }
  return order.map((value) => [value, counts.get(value)]);
}

/* ---------- Загрузка ---------- */

async function load() {
  const data = await fetchJSON("/api/admin/data");
  state.ingredients = data.ingredients;
  state.effects = data.effects;
  state.antagonists = data.antagonists;

  if (
    state.editingId !== null &&
    !state.ingredients.some((item) => item.id === state.editingId)
  ) {
    state.editingId = null;
    state.draftEffects = [];
    fillForm(null);
  }

  renderList();
  renderEditor();
  renderDictionary();
}

/* ---------- Список ---------- */

function renderList() {
  const query = state.query.trim().toLowerCase();
  const visible = state.ingredients.filter((item) =>
    item.name.toLowerCase().includes(query)
  );

  el.list.replaceChildren(
    ...visible.map((item) => {
      const li = document.createElement("li");

      const button = document.createElement("button");
      button.type = "button";
      button.dataset.id = String(item.id);
      if (item.id === state.editingId) button.setAttribute("aria-current", "true");

      const name = document.createElement("span");
      name.className = "name";
      name.textContent = item.name;
      name.title = item.name;

      const rarity = document.createElement("span");
      rarity.className = "rarity";
      rarity.dataset.rarity = item.rareness;
      rarity.textContent = item.rareness;

      const meta = document.createElement("span");
      meta.className = "meta";

      const omnisention = document.createElement("b");
      omnisention.textContent = `${item.omnisention > 0 ? "+" : ""}${item.omnisention}`;

      const effects = document.createElement("span");
      effects.className = "effects-summary";
      effects.textContent =
        aggregate(item.properties)
          .map(([effect, count]) => (count > 1 ? `${effect} ×${count}` : effect))
          .join(", ") || "без эффектов";

      meta.append(omnisention, effects);
      button.append(name, rarity, meta);
      button.addEventListener("click", () => selectIngredient(item.id));

      li.append(button);
      return li;
    })
  );

  el.listCount.textContent = `${visible.length} из ${state.ingredients.length}`;
}

/* ---------- Редактор ---------- */

function fillForm(item) {
  el.name.value = item ? item.name : "";
  el.omnisention.value = item ? item.omnisention : 0;
  el.rareness.value = item ? item.rareness : "A";
}

function selectIngredient(id) {
  const item = state.ingredients.find((candidate) => candidate.id === id);
  if (!item) return;

  state.editingId = item.id;
  state.draftEffects = [...item.properties];
  fillForm(item);
  clearErrors();
  renderList();
  renderEditor();
}

function resetForm() {
  state.editingId = null;
  state.draftEffects = [];
  fillForm(null);
  clearErrors();
  renderList();
  renderEditor();
  el.name.focus();
}

function renderEditor() {
  el.title.textContent = state.editingId
    ? "Редактирование ингредиента"
    : "Новый ингредиент";
  el.hint.textContent = state.editingId ? `id ${state.editingId}` : "";
  el.deleteButton.hidden = state.editingId === null;
  el.effectsCount.textContent = state.draftEffects.length
    ? `${state.draftEffects.length} шт.`
    : "";
  renderChips();
}

function renderChips() {
  const groups = aggregate(state.draftEffects);

  el.chips.replaceChildren(
    ...groups.map(([effect, count]) => {
      const chip = document.createElement("span");
      chip.className = "effect-chip";

      const label = document.createElement("span");
      label.textContent = effect;

      chip.append(label);

      if (count > 1) {
        const badge = document.createElement("span");
        badge.className = "effect-chip__count";
        badge.textContent = `×${count}`;
        chip.append(badge);
      }

      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "effect-chip__remove";
      remove.textContent = "×";
      remove.title = `Убрать «${effect}»`;
      remove.addEventListener("click", () => {
        // убираем одно вхождение, а не весь эффект
        const index = state.draftEffects.indexOf(effect);
        if (index !== -1) state.draftEffects.splice(index, 1);
        renderChips();
        renderEditor();
      });
      chip.append(remove);

      return chip;
    })
  );
}

function addDraftEffect(effect) {
  if (!effect) return;
  state.draftEffects.push(effect);
  renderChips();
  renderEditor();
}

/* ---------- Справочник ---------- */

function fillEffectSelects() {
  const selects = [el.effectSelect, el.pairA, el.pairB];

  for (const select of selects) {
    const previous = select.value;
    select.replaceChildren(
      ...state.effects.map((effect) => {
        const option = document.createElement("option");
        option.value = effect;
        option.textContent = effect;
        return option;
      })
    );
    if (previous && state.effects.includes(previous)) select.value = previous;
  }

  if (state.effects.length > 1 && el.pairB.value === el.pairA.value) {
    el.pairB.selectedIndex = 1;
  }
}

function renderDictionary() {
  fillEffectSelects();

  el.pairs.replaceChildren(
    ...state.antagonists.map((pair) => {
      const li = document.createElement("li");

      const first = document.createElement("b");
      first.textContent = pair.effect;

      const vs = document.createElement("span");
      vs.className = "vs";
      vs.textContent = "⇄";

      const second = document.createElement("b");
      second.textContent = pair.antieffect;

      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "remove";
      remove.textContent = "×";
      remove.title = "Удалить пару";
      remove.addEventListener("click", () => removePair(pair));

      li.append(first, vs, second, remove);
      return li;
    })
  );
}

/* ---------- Действия ---------- */

async function save(event) {
  event.preventDefault();
  if (state.saving) return;

  clearErrors();

  const payload = {
    name: el.name.value.trim(),
    omnisention: Number(el.omnisention.value),
    rareness: el.rareness.value,
    properties: state.draftEffects,
  };

  if (!payload.name) {
    showErrors("Название не может быть пустым.");
    el.name.focus();
    return;
  }

  state.saving = true;
  el.saveButton.disabled = true;
  el.saveButton.textContent = "Сохраняю…";

  try {
    const isUpdate = state.editingId !== null;
    const url = isUpdate
      ? `/api/admin/ingredients/${state.editingId}`
      : "/api/admin/ingredients";

    const data = await fetchJSON(url, {
      method: isUpdate ? "PUT" : "POST",
      body: JSON.stringify(payload),
    });

    await load();
    selectIngredient(data.ingredient.id);
    toast(isUpdate ? "Изменения сохранены" : "Ингредиент добавлен", true);
  } catch (error) {
    showErrors(error.message);
    toast(error.message);
  } finally {
    state.saving = false;
    el.saveButton.disabled = false;
    el.saveButton.textContent = "Сохранить";
  }
}

async function removeIngredient() {
  if (state.editingId === null) return;

  const item = state.ingredients.find((candidate) => candidate.id === state.editingId);
  const name = item ? item.name : "ингредиент";

  if (!window.confirm(`Удалить «${name}»? Зелья, где он был, считаться не будут.`)) {
    return;
  }

  try {
    await fetchJSON(`/api/admin/ingredients/${state.editingId}`, { method: "DELETE" });
    state.editingId = null;
    state.draftEffects = [];
    await load();
    resetForm();
    toast("Ингредиент удалён", true);
  } catch (error) {
    toast(error.message);
  }
}

async function createEffect() {
  const name = el.newEffect.value.trim();
  if (!name) {
    toast("Введите название эффекта");
    return;
  }

  try {
    await fetchJSON("/api/admin/effects", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
    el.newEffect.value = "";
    await load();
    el.effectSelect.value = name;
    toast(`Эффект «${name}» добавлен`, true);
  } catch (error) {
    toast(error.message);
  }
}

async function addPair() {
  const effect = el.pairA.value;
  const antieffect = el.pairB.value;

  if (!effect || !antieffect) return;

  try {
    await fetchJSON("/api/admin/antagonists", {
      method: "POST",
      body: JSON.stringify({ effect, antieffect }),
    });
    await load();
    toast("Пара добавлена", true);
  } catch (error) {
    toast(error.message);
  }
}

async function removePair(pair) {
  const params = new URLSearchParams({
    effect: pair.effect,
    antieffect: pair.antieffect,
  });

  try {
    await fetchJSON(`/api/admin/antagonists?${params}`, { method: "DELETE" });
    await load();
    toast("Пара удалена", true);
  } catch (error) {
    toast(error.message);
  }
}

/* ---------- События ---------- */

el.search.addEventListener("input", () => {
  state.query = el.search.value;
  renderList();
});

el.newButton.addEventListener("click", resetForm);
el.resetButton.addEventListener("click", resetForm);
el.form.addEventListener("submit", save);
el.deleteButton.addEventListener("click", removeIngredient);

el.effectAdd.addEventListener("click", () => addDraftEffect(el.effectSelect.value));
el.effectSelect.addEventListener("dblclick", () => addDraftEffect(el.effectSelect.value));

el.pairAdd.addEventListener("click", addPair);
el.newEffectAdd.addEventListener("click", createEffect);
el.newEffect.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    createEffect();
  }
});

el.pairA.addEventListener("change", () => {
  if (el.pairB.value === el.pairA.value) {
    const alternative = state.effects.find((effect) => effect !== el.pairA.value);
    if (alternative) el.pairB.value = alternative;
  }
});

/* ---------- Старт ---------- */

async function start() {
  try {
    await load();
    resetForm();
    el.status.textContent = "база подключена";
    el.status.dataset.state = "ok";
  } catch (error) {
    el.status.textContent = "нет связи с сервером";
    el.status.dataset.state = "error";
    toast(error.message);
  }
}

start();
