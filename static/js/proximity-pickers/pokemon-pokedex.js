/**
 * Pokémon Pokédex-style guess picker for proximity mode.
 */
const POKEMON_REGION_NAMES = {
  1: "Kanto",
  2: "Johto",
  3: "Hoenn",
  4: "Sinnoh",
  5: "Unova",
  6: "Kalos",
  7: "Alola",
  8: "Galar",
  9: "Paldea",
};

function readProximityPickerCatalog() {
  const script = document.getElementById("proximity-picker-catalog");
  if (!script?.textContent) return null;
  try {
    return JSON.parse(script.textContent);
  } catch {
    return null;
  }
}

function normalizePokemonCatalog(raw) {
  if (!raw || typeof raw !== "object") {
    return { generations: [], silhouette_url: "" };
  }

  const silhouetteUrl =
    raw.silhouette_url ||
    document.getElementById("proximity-game-data")?.dataset.defaultPortrait ||
    "";

  const generations = Array.isArray(raw.generations) ? raw.generations : [];
  if (!generations.length) {
    return { generations: [], silhouette_url: silhouetteUrl };
  }

  return {
    silhouette_url: silhouetteUrl,
    generations: generations.map((gen) => ({
      id: Number(gen.id ?? gen.generation ?? 0),
      region: gen.region || POKEMON_REGION_NAMES[gen.id] || `Gen ${gen.id}`,
      kicker: gen.kicker || `Gen ${gen.id}`,
      pokemon: (gen.pokemon || []).map((entry) => ({
        number: Number(entry.number ?? entry.id),
      })),
    })),
  };
}

function initPokemonPokedexPicker(pickerEl, hiddenInput, submitBtn) {
  if (!pickerEl || !hiddenInput) return null;

  const catalog = normalizePokemonCatalog(readProximityPickerCatalog());
  const silhouetteUrl = catalog.silhouette_url;
  let currentValue = null;

  const displayEl = pickerEl.querySelector(".proximity-picker__value");
  const bodyEl = pickerEl.querySelector(".proximity-picker__body");

  let shellEl = null;
  let toolbarEl = null;
  let panelEl = null;
  let hintEl = null;

  function clearValue() {
    currentValue = null;
    hiddenInput.value = "";
    if (displayEl) {
      displayEl.textContent = "—";
    }
    if (submitBtn) {
      submitBtn.disabled = true;
    }
    pickerEl.dispatchEvent(
      new CustomEvent("proximity-guess-change", { detail: { value: null } })
    );
  }

  function applyValue(value) {
    currentValue = value;
    hiddenInput.value = String(value);
    if (displayEl) {
      displayEl.textContent = String(value);
    }
    if (submitBtn) {
      submitBtn.disabled = false;
    }
    pickerEl.dispatchEvent(
      new CustomEvent("proximity-guess-change", { detail: { value: currentValue } })
    );
  }

  function appendSilhouette(cell) {
    if (silhouetteUrl) {
      const img = document.createElement("img");
      img.src = silhouetteUrl;
      img.alt = "";
      img.className = "proximity-pokedex__cell-img proximity-pokedex__cell-img--silhouette";
      img.loading = "lazy";
      img.decoding = "async";
      cell.appendChild(img);
      return;
    }
    const placeholder = document.createElement("span");
    placeholder.className = "proximity-pokedex__cell-placeholder";
    placeholder.setAttribute("aria-hidden", "true");
    cell.appendChild(placeholder);
  }

  function selectPokemon(cell, grid, number) {
    if (currentValue === number) {
      grid.querySelectorAll(".proximity-pokedex__cell").forEach((item) => {
        item.classList.remove("is-selected");
        item.setAttribute("aria-pressed", "false");
      });
      clearValue();
      return;
    }
    grid.querySelectorAll(".proximity-pokedex__cell").forEach((item) => {
      const selected = item === cell;
      item.classList.toggle("is-selected", selected);
      item.setAttribute("aria-pressed", selected ? "true" : "false");
    });
    applyValue(number);
  }

  function triggerOpenAnimation() {
    if (!shellEl) return;
    shellEl.classList.remove("proximity-pokedex--opening");
    void shellEl.offsetWidth;
    shellEl.classList.add("proximity-pokedex--opening");
    shellEl.addEventListener(
      "animationend",
      () => {
        shellEl.classList.remove("proximity-pokedex--opening");
      },
      { once: true }
    );
  }

  function ensurePokedexShell() {
    if (shellEl) return;

    hintEl = document.createElement("p");
    hintEl.className = "proximity-picker__hint proximity-pokedex__hint";
    hintEl.textContent = "Elige una región para abrir la Pokédex";

    shellEl = document.createElement("div");
    shellEl.className = "proximity-pokedex";

    const lights = document.createElement("div");
    lights.className = "proximity-pokedex__lights";
    lights.setAttribute("aria-hidden", "true");
    lights.innerHTML =
      '<span class="proximity-pokedex__light proximity-pokedex__light--blue"></span>' +
      '<span class="proximity-pokedex__light proximity-pokedex__light--red"></span>' +
      '<span class="proximity-pokedex__light proximity-pokedex__light--yellow"></span>';

    const screenEl = document.createElement("div");
    screenEl.className = "proximity-pokedex__screen";

    toolbarEl = document.createElement("div");
    toolbarEl.className = "proximity-pokedex__toolbar";
    toolbarEl.hidden = true;

    panelEl = document.createElement("div");
    panelEl.className = "proximity-pokedex__panel";

    screenEl.append(toolbarEl, panelEl);

    const hinge = document.createElement("div");
    hinge.className = "proximity-pokedex__hinge";
    hinge.setAttribute("aria-hidden", "true");

    shellEl.append(lights, screenEl, hinge);
    bodyEl.append(hintEl, shellEl);
  }

  function clearPanel() {
    if (panelEl) panelEl.innerHTML = "";
  }

  function showRegionPanel() {
    ensurePokedexShell();
    shellEl.classList.remove("proximity-pokedex--open");
    toolbarEl.hidden = true;
    toolbarEl.innerHTML = "";
    if (hintEl) hintEl.hidden = false;
    clearPanel();

    const grid = document.createElement("div");
    grid.className = "proximity-pokedex__regions";

    catalog.generations.forEach((generation) => {
      const tile = document.createElement("button");
      tile.type = "button";
      tile.className = "proximity-pokedex__region";
      tile.setAttribute("aria-label", generation.region);

      const kicker = document.createElement("span");
      kicker.className = "proximity-pokedex__region-kicker";
      kicker.textContent = generation.kicker;

      const label = document.createElement("span");
      label.className = "proximity-pokedex__region-label";
      label.textContent = generation.region;

      const count = document.createElement("span");
      count.className = "proximity-pokedex__region-count";
      count.textContent = `${generation.pokemon.length} Pokémon`;

      tile.append(kicker, label, count);
      tile.addEventListener("click", () => showPokemonPanel(generation));
      grid.appendChild(tile);
    });

    panelEl.appendChild(grid);
  }

  function showPokemonPanel(generation) {
    ensurePokedexShell();
    shellEl.classList.add("proximity-pokedex--open");
    if (hintEl) hintEl.hidden = true;
    clearPanel();

    const back = document.createElement("button");
    back.type = "button";
    back.className = "proximity-pokedex__back-btn";
    back.setAttribute("aria-label", "Cambiar región");
    back.textContent = "←";

    const title = document.createElement("p");
    title.className = "proximity-pokedex__title";
    title.textContent = generation.region;

    toolbarEl.innerHTML = "";
    toolbarEl.append(back, title);
    toolbarEl.hidden = false;
    back.addEventListener("click", showRegionPanel);

    const scroll = document.createElement("div");
    scroll.className = "proximity-pokedex__scroll";

    const grid = document.createElement("div");
    grid.className = "proximity-pokedex__grid";
    grid.setAttribute("role", "listbox");
    grid.setAttribute("aria-label", `Pokémon de ${generation.region}`);

    generation.pokemon.forEach((entry) => {
      const cell = document.createElement("button");
      cell.type = "button";
      cell.className = "proximity-pokedex__cell";
      cell.setAttribute("role", "option");
      cell.dataset.value = String(entry.number);
      cell.setAttribute("aria-label", `Nº ${entry.number}`);

      if (currentValue === entry.number) {
        cell.classList.add("is-selected");
        cell.setAttribute("aria-pressed", "true");
      }

      appendSilhouette(cell);

      const number = document.createElement("span");
      number.className = "proximity-pokedex__number";
      number.textContent = String(entry.number).padStart(3, "0");
      cell.appendChild(number);

      cell.addEventListener("click", () => selectPokemon(cell, grid, entry.number));
      grid.appendChild(cell);
    });

    scroll.appendChild(grid);
    panelEl.appendChild(scroll);
    triggerOpenAnimation();
  }

  function renderInitialState() {
    if (!bodyEl) return;
    bodyEl.innerHTML = "";

    if (!catalog.generations.length) {
      const empty = document.createElement("p");
      empty.className = "proximity-picker__hint";
      empty.textContent = "No hay Pokémon disponibles en el catálogo.";
      bodyEl.appendChild(empty);
      return;
    }

    showRegionPanel();
  }

  if (submitBtn) {
    submitBtn.disabled = true;
  }
  if (displayEl) {
    displayEl.textContent = "—";
  }

  renderInitialState();

  return {
    getValue: () => currentValue,
    setValue(value) {
      const numericValue = Number(value);
      if (!Number.isFinite(numericValue)) {
        clearValue();
        return;
      }
      applyValue(numericValue);
    },
  };
}

window.initPokemonPokedexPicker = initPokemonPokedexPicker;
