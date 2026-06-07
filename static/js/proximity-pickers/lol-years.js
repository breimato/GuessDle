/**
 * League of Legends year picker for proximity mode.
 */
function readLolYearsCatalog() {
  const script = document.getElementById("proximity-picker-catalog");
  if (!script?.textContent) return null;
  try {
    return JSON.parse(script.textContent);
  } catch {
    return null;
  }
}

function normalizeLolYearsCatalog(catalog) {
  if (!catalog || typeof catalog !== "object") {
    return { years: [], iconUrl: "" };
  }

  const iconUrl =
    catalog.icon_url ||
    document.getElementById("proximity-game-data")?.dataset.defaultPortrait ||
    "";

  if (Array.isArray(catalog.years) && catalog.years.length) {
    return {
      iconUrl,
      years: catalog.years
        .map((entry) => Number(entry.year ?? entry.guess_value))
        .filter((year) => Number.isFinite(year))
        .sort((a, b) => a - b),
    };
  }

  const discreteScript = document.getElementById("proximity-discrete-values");
  if (discreteScript?.textContent) {
    try {
      const values = JSON.parse(discreteScript.textContent);
      if (Array.isArray(values)) {
        return {
          iconUrl,
          years: values
            .map((year) => Number(year))
            .filter((year) => Number.isFinite(year))
            .sort((a, b) => a - b),
        };
      }
    } catch {
      /* fallback below */
    }
  }

  return { years: [], iconUrl };
}

function initLolYearsPicker(pickerEl, hiddenInput, submitBtn) {
  if (!pickerEl || !hiddenInput) return null;

  const catalog = normalizeLolYearsCatalog(readLolYearsCatalog());
  const years = catalog.years;
  const iconUrl = catalog.iconUrl;
  let currentValue = null;

  const displayEl = pickerEl.querySelector(".proximity-picker__value");
  const bodyEl = pickerEl.querySelector(".proximity-picker__body");
  pickerEl.classList.add("proximity-picker--lol", "proximity-filters--lol");

  let shellEl = null;
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

  function ensureLolShell() {
    if (shellEl) return;

    hintEl = document.createElement("p");
    hintEl.className = "proximity-picker__hint proximity-picker-frame__hint";
    hintEl.textContent = "Elige un año de lanzamiento";

    shellEl = document.createElement("div");
    shellEl.className = "proximity-picker-frame proximity-picker-frame--lol";

    panelEl = document.createElement("div");
    panelEl.className =
      "proximity-picker-frame__scroll proximity-filters__scroll proximity-filters__scroll--years";

    shellEl.appendChild(panelEl);
    bodyEl.append(hintEl, shellEl);
  }

  function renderYearTiles() {
    ensureLolShell();
    panelEl.innerHTML = "";

    if (!years.length) {
      const empty = document.createElement("p");
      empty.className = "proximity-picker__hint";
      empty.textContent = "No hay años disponibles en el catálogo.";
      panelEl.appendChild(empty);
      return;
    }

    const grid = document.createElement("div");
    grid.className = "proximity-filter-tile-grid proximity-filter-tile-grid--lol-years";
    grid.setAttribute("role", "listbox");
    grid.setAttribute("aria-label", "Años de lanzamiento");

    years.forEach((year) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className =
        "proximity-filter-tile proximity-filter-tile--lol-year proximity-picker-frame__tile";
      btn.dataset.value = String(year);
      btn.setAttribute("role", "option");
      btn.setAttribute("aria-label", `Año ${year}`);

      if (currentValue === year) {
        btn.classList.add("is-selected");
        btn.setAttribute("aria-pressed", "true");
      }

      const face = document.createElement("span");
      face.className = "proximity-filter-tile__face";

      if (iconUrl) {
        const watermark = document.createElement("img");
        watermark.src = iconUrl;
        watermark.alt = "";
        watermark.className = "proximity-filter-tile__watermark";
        watermark.setAttribute("aria-hidden", "true");
        watermark.decoding = "async";
        face.appendChild(watermark);
      }

      const label = document.createElement("span");
      label.className = "proximity-filter-tile__label";
      label.textContent = String(year);
      face.appendChild(label);

      btn.appendChild(face);
      btn.addEventListener("click", () => {
        if (currentValue === year) {
          grid.querySelectorAll(".proximity-picker-frame__tile").forEach((item) => {
            item.classList.remove("is-selected");
            item.setAttribute("aria-pressed", "false");
          });
          clearValue();
          return;
        }
        grid.querySelectorAll(".proximity-picker-frame__tile").forEach((item) => {
          const selected = item === btn;
          item.classList.toggle("is-selected", selected);
          item.setAttribute("aria-pressed", selected ? "true" : "false");
        });
        applyValue(year);
      });
      grid.appendChild(btn);
    });

    panelEl.appendChild(grid);
  }

  function renderInitialState() {
    if (!bodyEl) return;
    bodyEl.innerHTML = "";
    renderYearTiles();
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
        if (panelEl) {
          panelEl.querySelectorAll(".proximity-picker-frame__tile").forEach((item) => {
            item.classList.remove("is-selected");
            item.setAttribute("aria-pressed", "false");
          });
        }
        clearValue();
        return;
      }
      applyValue(numericValue);
      const tile = panelEl?.querySelector(
        `.proximity-picker-frame__tile[data-value="${numericValue}"]`
      );
      if (!tile || !panelEl) return;
      panelEl.querySelectorAll(".proximity-picker-frame__tile").forEach((item) => {
        const selected = item === tile;
        item.classList.toggle("is-selected", selected);
        item.setAttribute("aria-pressed", selected ? "true" : "false");
      });
    },
  };
}

window.initLolYearsPicker = initLolYearsPicker;
window.initLolChampionsPicker = initLolYearsPicker;
