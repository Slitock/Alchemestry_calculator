/* Алхимический котёл — клиент.
 * Вся логика варки живёт на сервере (/api/brew), здесь только состояние
 * котла и отрисовка. Никаких внешних библиотек и CDN: страница должна
 * работать в локальной сети без интернета.
 */

const RARITIES = ["E", "D", "C", "B", "A", "S"];
const STORAGE_KEY = "alchemy.cauldron.v1";

const state = {
  catalog: [],
  rules: { conflicts: [], gradation: [], max_count: 99 },
  counts: new Map(), // имя ингредиента -> количество
  query: "",
  rarity: "all",
  brewing: false,
  tab: "ingredients", // активная вкладка на телефоне
};

const el = {
  status: document.getElementById("server-status"),
  search: document.getElementById("search"),
  rarityFilter: document.getElementById("rarity-filter"),
  list: document.getElementById("ingredient-list"),
  listEmpty: document.getElementById("ingredients-empty"),
  listCount: document.getElementById("ingredients-count"),
  template: document.getElementById("ingredient-template"),
  cauldron: document.getElementById("cauldron"),
  cauldronBadge: document.getElementById("cauldron-badge"),
  cauldronHint: document.getElementById("cauldron-hint"),
  cauldronContents: document.getElementById("cauldron-contents"),
  statCount: document.getElementById("stat-count"),
  statOmnisention: document.getElementById("stat-omnisention"),
  brewButton: document.getElementById("brew-button"),
  clearButton: document.getElementById("clear-button"),
  conflictList: document.getElementById("conflict-list"),
  gradationTable: document.querySelector("#gradation-table tbody"),
  dialog: document.getElementById("result-dialog"),
  resultTitle: document.getElementById("result-title"),
  resultBody: document.getElementById("result-body"),
  resultClose: document.getElementById("result-close"),
  resultAgain: document.getElementById("result-again"),
  resultClear: document.getElementById("result-clear"),
  toast: document.getElementById("toast"),
  tabs: document.querySelectorAll(".mobile-tab"),
  panels: document.querySelectorAll(".layout > .panel"),
  tabBadge: document.getElementById("tab-badge"),
  barCount: document.getElementById("bar-count"),
  barOmn: document.getElementById("bar-omn"),
  barBrew: document.getElementById("bar-brew"),
  barClear: document.getElementById("bar-clear"),
  barSummary: document.getElementById("bar-summary"),
};

/* ---------- Утилиты ---------- */

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[char]);
}

function totalCount() {
  let total = 0;
  for (const count of state.counts.values()) total += count;
  return total;
}

function rawOmnisention() {
  let total = 0;
  for (const [name, count] of state.counts) {
    const item = state.catalog.find((ing) => ing.name === name);
    if (item) total += item.omnisention * count;
  }
  return total;
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

let toastTimer = null;
function toast(message) {
  el.toast.textContent = message;
  el.toast.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.toast.hidden = true; }, 4200);
}

/* ---------- Сохранение котла ---------- */

function saveCauldron() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify([...state.counts]));
  } catch {
    /* приватный режим браузера — просто не сохраняем */
  }
}

function loadCauldron() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return;
    const entries = JSON.parse(raw);
    if (!Array.isArray(entries)) return;
    for (const entry of entries) {
      if (!Array.isArray(entry)) continue;
      const [name, count] = entry;
      if (typeof name !== "string" || !Number.isInteger(count) || count <= 0) continue;
      state.counts.set(name, Math.min(count, state.rules.max_count));
    }
  } catch {
    /* битое значение в localStorage — начинаем с пустого котла */
  }
}

/* ---------- Отрисовка: ингредиенты ---------- */

function renderRarityFilter() {
  const present = RARITIES.filter((rarity) =>
    state.catalog.some((ing) => ing.rareness === rarity)
  );
  const values = ["all", ...present];

  el.rarityFilter.replaceChildren(
    ...values.map((value) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "rarity-chip";
      button.dataset.rarity = value;
      button.textContent = value === "all" ? "все" : value;
      button.setAttribute("aria-pressed", String(state.rarity === value));
      if (value !== "all") button.style.setProperty("--rc", `var(--rarity-${value.toLowerCase()})`);
      button.addEventListener("click", () => {
        state.rarity = value;
        renderRarityFilter();
        renderIngredients();
      });
      return button;
    })
  );
}

function matchesFilter(ingredient) {
  if (state.rarity !== "all" && ingredient.rareness !== state.rarity) return false;
  const query = state.query.trim().toLowerCase();
  if (!query) return true;
  if (ingredient.name.toLowerCase().includes(query)) return true;
  return ingredient.properties.some((property) => property.toLowerCase().includes(query));
}

function renderIngredients() {
  const visible = state.catalog.filter(matchesFilter);
  const fragment = document.createDocumentFragment();

  for (const ingredient of visible) {
    const node = el.template.content.firstElementChild.cloneNode(true);
    const count = state.counts.get(ingredient.name) ?? 0;

    node.dataset.name = ingredient.name;
    node.dataset.active = String(count > 0);
    node.querySelector(".ingredient__name").textContent = ingredient.name;

    const rarity = node.querySelector(".rarity");
    rarity.textContent = ingredient.rareness;
    rarity.dataset.rarity = ingredient.rareness;
    rarity.title = `Редкость ${ingredient.rareness}`;

    const omnisention = node.querySelector(".ingredient__omnisention");
    omnisention.textContent = `${ingredient.omnisention > 0 ? "+" : ""}${ingredient.omnisention}`;
    omnisention.dataset.negative = String(ingredient.omnisention < 0);
    omnisention.title = "Омнисенция ингредиента";

    const effectsText = aggregate(ingredient.properties)
      .map(([name, times]) => (times > 1 ? `${name} ×${times}` : name))
      .join(", ");
    const effectsLabel = node.querySelector(".ingredient__effects");
    effectsLabel.textContent = effectsText;
    effectsLabel.title = effectsText;

    const stepper = node.querySelector(".stepper");
    stepper.hidden = count === 0;
    node.querySelector(".stepper__value").textContent = count;

    fragment.append(node);
  }

  el.list.replaceChildren(fragment);
  el.listEmpty.hidden = visible.length > 0;
  el.listCount.textContent = `${visible.length} из ${state.catalog.length}`;
}

/* ---------- Отрисовка: котёл ---------- */

function setTab(tab) {
  state.tab = tab;
  for (const button of el.tabs) {
    button.setAttribute("aria-pressed", String(button.dataset.tab === tab));
  }
  for (const panel of el.panels) {
    panel.dataset.mobileActive = String(panel.dataset.panel === tab);
  }
  if (tab === "cauldron") window.scrollTo({ top: 0, behavior: "smooth" });
}

function renderCauldron() {
  const entries = [...state.counts.entries()].filter(([, count]) => count > 0);
  const items = totalCount();
  const empty = items === 0;

  el.cauldron.dataset.empty = String(empty);
  el.cauldronBadge.hidden = empty;
  el.cauldronBadge.textContent = items;
  el.cauldronHint.textContent = empty ? "Котёл пуст" : "Нажми, чтобы сварить";

  el.statCount.textContent = items;
  el.statOmnisention.textContent = rawOmnisention();

  el.brewButton.disabled = empty || state.brewing;
  el.clearButton.disabled = empty || state.brewing;

  el.barCount.textContent = items;
  el.barOmn.textContent = `${rawOmnisention()} омнисенции`;
  el.barBrew.disabled = empty || state.brewing;
  el.barClear.disabled = empty || state.brewing;
  el.tabBadge.hidden = empty;
  el.tabBadge.textContent = items;

  el.cauldronContents.replaceChildren(
    ...entries.map(([name, count]) => {
      const chip = document.createElement("span");
      chip.className = "chip";

      const label = document.createElement("span");
      label.textContent = name;

      const counter = document.createElement("span");
      counter.className = "chip__count";
      counter.textContent = `×${count}`;

      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "chip__remove";
      remove.textContent = "×";
      remove.title = `Убрать ${name} из котла`;
      remove.addEventListener("click", () => setCount(name, 0));

      chip.append(label, counter, remove);
      return chip;
    })
  );
}

/* ---------- Состояние котла ---------- */

function setCount(name, count) {
  const limit = state.rules.max_count || 99;
  const next = Math.max(0, Math.min(count, limit));
  if (next === 0) state.counts.delete(name);
  else state.counts.set(name, next);

  saveCauldron();
  renderIngredients();
  renderCauldron();
}

function changeCount(name, delta) {
  setCount(name, (state.counts.get(name) ?? 0) + delta);
}

function clearCauldron() {
  state.counts.clear();
  saveCauldron();
  renderIngredients();
  renderCauldron();
}

/* ---------- Правила (правая колонка) ---------- */

function renderRules() {
  if (!el.conflictList) return;

  el.conflictList.replaceChildren(
    ...state.rules.conflicts.map((pair) => {
      const item = document.createElement("li");
      item.innerHTML =
        `<b>${escapeHtml(pair.effect)}</b>` +
        `<span class="pairs__vs">⇄</span>` +
        `<b>${escapeHtml(pair.antieffect)}</b>`;
      return item;
    })
  );

  if (el.gradationTable) {
    el.gradationTable.replaceChildren(
      ...state.rules.gradation.map((row) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td>${row.effects}</td><td>${row.min} – ${row.max}</td>`;
        return tr;
      })
    );
  }
}

/* ---------- Варка ---------- */

function renderResult(data) {
  const sections = [];

  const recept = document.createElement("div");
  recept.innerHTML =
    `<p class="section-title">Рецепт</p>` +
    `<ul class="recept">` +
    data.recept
      .map((entry) => {
        const crystal = entry.startsWith("кристал");
        return `<li${crystal ? ' data-crystal="true"' : ""}>${escapeHtml(entry)}</li>`;
      })
      .join("") +
    `</ul>`;
  sections.push(recept);

  const totalEffects = data.effects.reduce((sum, effect) => sum + effect.count, 0);
  const effects = document.createElement("div");
  effects.innerHTML =
    `<p class="section-title">Эффекты (${totalEffects})</p>` +
    (data.effects.length
      ? `<ul class="effects">` +
        data.effects
          .map(
            (effect) =>
              `<li>${escapeHtml(effect.name)}` +
              (effect.count > 1 ? `<span class="effects__count">×${effect.count}</span>` : "") +
              `</li>`
          )
          .join("") +
        `</ul>`
      : `<p class="muted">Эффектов не осталось — они погасили друг друга.</p>`);
  sections.push(effects);

  const delta = data.omnisention - data.raw_omnisention;
  const crystalText = data.crystals.length
    ? data.crystals
        .map(
          (crystal) =>
            `<span class="crystal crystal--${crystal.type === "ихор" ? "ihor" : "cenom"}">` +
            `${escapeHtml(crystal.type)} ×${crystal.count}</span>`
        )
        .join(" ")
    : `<span class="muted">не потребовались</span>`;

  const omnisention = document.createElement("div");
  omnisention.className = "omnisention-card";
  omnisention.innerHTML =
    `<div class="omnisention-card__value"${data.omnisention < 0 ? ' data-negative="true"' : ""}>` +
    `${data.omnisention}</div>` +
    `<div class="omnisention-card__detail">` +
    `<span>Сырая сумма ингредиентов: <b>${data.raw_omnisention}</b></span>` +
    `<span>Поправка кристаллами: <b>${delta > 0 ? "+" : ""}${delta}</b></span>` +
    `<span>Кристаллы: ${crystalText}</span>` +
    `</div>`;
  sections.push(omnisention);

  if (data.removed.length) {
    const removed = document.createElement("div");
    removed.innerHTML =
      `<p class="section-title">Погашенные конфликты</p>` +
      `<ul class="removed">` +
      data.removed
        .map(
          (pair) =>
            `<li><b>${escapeHtml(pair.effect)}</b>` +
            `<span class="removed__x">⇄</span>` +
            `<b>${escapeHtml(pair.antieffect)}</b>` +
            (pair.count > 1 ? ` ×${pair.count}` : "") +
            `</li>`
        )
        .join("") +
      `</ul>`;
    sections.push(removed);
  }

  el.resultBody.replaceChildren(...sections);
  el.resultTitle.textContent = data.effects.length ? "Зелье готово" : "Пустая настойка";
}

async function brew() {
  if (state.brewing) return;

  const ingredients = [...state.counts.entries()].map(([name, count]) => ({ name, count }));
  if (!ingredients.length) {
    toast("Котёл пуст — не из чего варить.");
    return;
  }

  state.brewing = true;
  el.cauldron.dataset.brewing = "true";
  el.brewButton.disabled = true;
  el.clearButton.disabled = true;

  try {
    const [response] = await Promise.all([
      fetch("/api/brew", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ingredients }),
      }),
      new Promise((resolve) => setTimeout(resolve, 550)), // чтобы варка была видимой
    ]);

    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || "Сервер не смог сварить зелье.");

    renderResult(data);
    if (!el.dialog.open) el.dialog.showModal();
  } catch (error) {
    toast(error.message || "Ошибка соединения с сервером.");
  } finally {
    state.brewing = false;
    el.cauldron.dataset.brewing = "false";
    renderCauldron();
  }
}

/* ---------- События ---------- */

el.search.addEventListener("input", () => {
  state.query = el.search.value;
  renderIngredients();
});

el.list.addEventListener("click", (event) => {
  const trigger = event.target.closest("[data-action]");
  if (!trigger) return;
  const item = trigger.closest(".ingredient");
  if (!item) return;

  const name = item.dataset.name;
  if (trigger.dataset.action === "dec") changeCount(name, -1);
  else changeCount(name, 1);
});

el.cauldron.addEventListener("click", brew);
el.brewButton.addEventListener("click", brew);
el.clearButton.addEventListener("click", clearCauldron);
el.barBrew.addEventListener("click", () => {
  setTab("cauldron");
  brew();
});
el.barSummary.addEventListener("click", () => setTab("cauldron"));
el.barClear.addEventListener("click", clearCauldron);

for (const button of el.tabs) {
  button.addEventListener("click", () => setTab(button.dataset.tab));
}

el.resultClose.addEventListener("click", () => el.dialog.close());
el.resultAgain.addEventListener("click", () => el.dialog.close());
el.resultClear.addEventListener("click", () => {
  el.dialog.close();
  clearCauldron();
});

el.dialog.addEventListener("click", (event) => {
  if (event.target === el.dialog) el.dialog.close();
});

/* ---------- Старт ---------- */

async function start() {
  try {
    const [catalogResponse, rulesResponse] = await Promise.all([
      fetch("/api/ingredients"),
      fetch("/api/rules"),
    ]);
    if (!catalogResponse.ok || !rulesResponse.ok) throw new Error("Сервер вернул ошибку.");

    const catalog = await catalogResponse.json();
    const rules = await rulesResponse.json();

    state.catalog = catalog.ingredients || [];
    state.rules = { ...state.rules, ...rules };

    loadCauldron();
    // на случай, если ингредиент убрали из базы
    for (const name of [...state.counts.keys()]) {
      if (!state.catalog.some((ing) => ing.name === name)) state.counts.delete(name);
    }

    renderRarityFilter();
    renderIngredients();
    renderCauldron();
    renderRules();
    setTab(state.tab);

    el.status.textContent = "готово";
    el.status.dataset.state = "ok";
  } catch (error) {
    el.status.textContent = "нет связи с сервером";
    el.status.dataset.state = "error";
    toast(error.message || "Не удалось загрузить данные.");
  }
}

start();
