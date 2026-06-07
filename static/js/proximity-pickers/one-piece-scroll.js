/**
 * One Piece proximity picker: arc tiles → pirate scroll of chapters/episodes.
 */
function readOnePiecePickerCatalog() {
  const script = document.getElementById("proximity-picker-catalog");
  if (!script?.textContent) return null;
  try {
    return JSON.parse(script.textContent);
  } catch {
    return null;
  }
}

function normalizeOnePieceCatalog(catalog) {
  if (!catalog || typeof catalog !== "object") {
    return [];
  }

  if (!Array.isArray(catalog.groups)) {
    return [];
  }

  return catalog.groups.map((group) => ({
    slug: group.id || group.slug || "",
    label: group.label || group.id || "",
    entries: (group.entries || [])
      .map((entry) => ({
        name: entry.name || "",
        guess_value: Number(entry.guess_value),
      }))
      .filter((entry) => Number.isFinite(entry.guess_value)),
  }));
}

function initOnePieceScrollPicker(pickerEl, hiddenInput, submitBtn) {
  if (!pickerEl || !hiddenInput) return null;

  const catalog = readOnePiecePickerCatalog();
  const arcs = normalizeOnePieceCatalog(catalog);
  const unit = pickerEl.dataset.valueUnit || catalog?.value_unit || "capítulo";
  const sceneImage = catalog?.scene_image_url || "/static/img/one-piece-menu.jpg";

  let currentValue = null;
  let selectedArc = null;

  const displayEl = pickerEl.querySelector(".proximity-picker__value");
  const bodyEl = pickerEl.querySelector(".proximity-picker__body");
  pickerEl.classList.add("proximity-picker--one-piece", "proximity-filters--one-piece");

  let shellEl = null;
  let toolbarEl = null;
  let panelEl = null;
  let hintEl = null;

  function unitPrefix() {
    if (unit === "episodio") return "Ep.";
    if (unit === "capítulo" || unit === "capitulo") return "Cap.";
    return unit;
  }

  function formatGuessValue(value) {
    return `${unitPrefix()} ${String(value).padStart(3, "0")}`;
  }

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

  function setValue(value) {
    if (value === null || value === undefined || value === "") {
      clearValue();
      return;
    }
    currentValue = value;
    hiddenInput.value = String(value);
    if (displayEl) {
      displayEl.textContent = formatGuessValue(value);
    }
    if (submitBtn) {
      submitBtn.disabled = false;
    }
    pickerEl.dispatchEvent(
      new CustomEvent("proximity-guess-change", { detail: { value: currentValue } })
    );
  }

  function entriesForArc(arcSlug) {
    const arc = arcs.find((row) => row.slug === arcSlug);
    if (!arc) return [];
    return [...arc.entries].sort((a, b) => a.guess_value - b.guess_value);
  }

  function arcCount(arcSlug) {
    return entriesForArc(arcSlug).length;
  }

  function triggerOpenAnimation() {
    if (!shellEl) return;
    shellEl.classList.remove("proximity-picker-frame--opening");
    void shellEl.offsetWidth;
    shellEl.classList.add("proximity-picker-frame--opening");
    shellEl.addEventListener(
      "animationend",
      () => {
        shellEl.classList.remove("proximity-picker-frame--opening");
      },
      { once: true }
    );
  }

  function ensureOnePieceShell() {
    if (shellEl) return;

    hintEl = document.createElement("p");
    hintEl.className = "proximity-picker__hint proximity-picker-frame__hint";
    hintEl.textContent = "Elige un arco para ver sus capítulos o episodios";

    shellEl = document.createElement("div");
    shellEl.className = "proximity-picker-frame proximity-picker-frame--one-piece";

    const panel = document.createElement("div");
    panel.className = "proximity-picker-frame__content";

    toolbarEl = document.createElement("div");
    toolbarEl.className = "proximity-picker-frame__toolbar";
    toolbarEl.hidden = true;

    panelEl = document.createElement("div");
    panelEl.className = "proximity-picker-frame__body";

    panel.append(toolbarEl, panelEl);
    shellEl.appendChild(panel);
    bodyEl.append(hintEl, shellEl);
  }

  function clearPanel() {
    if (panelEl) panelEl.innerHTML = "";
  }

  function showArcPanel() {
    ensureOnePieceShell();
    selectedArc = null;
    shellEl.classList.remove("proximity-picker-frame--open");
    toolbarEl.hidden = true;
    toolbarEl.innerHTML = "";
    if (hintEl) hintEl.hidden = false;
    clearPanel();

    const scroll = document.createElement("div");
    scroll.className =
      "proximity-picker-frame__scroll proximity-filters__scroll proximity-filters__scroll--arcs";

    const grid = document.createElement("div");
    grid.className = "proximity-filter-tile-grid proximity-picker__arc-grid";
    grid.setAttribute("role", "listbox");
    grid.setAttribute("aria-label", "Arcos disponibles");

    arcs.forEach((arc) => {
      const count = arcCount(arc.slug);
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "proximity-filter-tile proximity-filter-tile--arc proximity-picker__arc-tile";
      btn.dataset.arcSlug = arc.slug;
      btn.setAttribute("role", "option");

      const face = document.createElement("span");
      face.className = "proximity-filter-tile__face";

      const watermark = document.createElement("img");
      watermark.src = sceneImage;
      watermark.alt = "";
      watermark.className =
        "proximity-filter-tile__watermark proximity-filter-tile__watermark--scene";
      watermark.setAttribute("aria-hidden", "true");
      watermark.decoding = "async";

      const label = document.createElement("span");
      label.className = "proximity-filter-tile__label";
      label.textContent = arc.label;

      if (count > 0) {
        const meta = document.createElement("span");
        meta.className = "proximity-filter-tile__hint";
        meta.textContent = `${count} ${count === 1 ? "número" : "números"}`;
        face.append(watermark, label, meta);
      } else {
        face.append(watermark, label);
      }

      btn.append(face);
      btn.addEventListener("click", () => showScrollPanel(arc.slug, arc.label));
      grid.appendChild(btn);
    });

    if (!arcs.length) {
      const empty = document.createElement("p");
      empty.className = "arcade-text-muted proximity-filters__empty";
      empty.textContent = "No hay arcos en el catálogo del pool.";
      grid.appendChild(empty);
    }

    scroll.appendChild(grid);
    panelEl.appendChild(scroll);
  }

  function showScrollPanel(arcSlug, arcLabel) {
    ensureOnePieceShell();
    selectedArc = arcSlug;
    shellEl.classList.add("proximity-picker-frame--open");
    if (hintEl) hintEl.hidden = true;
    clearPanel();

    const back = document.createElement("button");
    back.type = "button";
    back.className = "proximity-picker-frame__back arcade-btn arcade-btn--secondary";
    back.setAttribute("aria-label", "Cambiar arco");
    back.textContent = "←";

    const title = document.createElement("p");
    title.className = "proximity-picker-frame__legend";
    title.textContent = arcLabel || arcSlug;

    toolbarEl.innerHTML = "";
    toolbarEl.append(back, title);
    toolbarEl.hidden = false;
    back.addEventListener("click", showArcPanel);

    const entries = entriesForArc(arcSlug);

    const scroll = document.createElement("div");
    scroll.className = "proximity-picker-frame__scroll proximity-scroll";
    scroll.setAttribute("role", "listbox");
    scroll.setAttribute(
      "aria-label",
      `${unit === "episodio" ? "Episodios" : "Capítulos"} de ${arcLabel || arcSlug}`
    );

    const list = document.createElement("div");
    list.className = "proximity-scroll__list proximity-scroll__list--numeric";

    entries.forEach((entry) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "proximity-scroll__entry proximity-scroll__entry--numeric";
      btn.dataset.value = String(entry.guess_value);
      btn.setAttribute("role", "option");
      const formattedValue = formatGuessValue(entry.guess_value);
      btn.setAttribute("aria-label", formattedValue);

      if (currentValue === entry.guess_value) {
        btn.classList.add("is-selected");
        btn.setAttribute("aria-selected", "true");
      }

      const valueEl = document.createElement("span");
      valueEl.className = "proximity-scroll__entry-value";
      valueEl.textContent = formattedValue;

      btn.append(valueEl);

      btn.addEventListener("click", () => {
        if (currentValue === entry.guess_value) {
          list.querySelectorAll(".proximity-scroll__entry").forEach((row) => {
            row.classList.remove("is-selected");
            row.setAttribute("aria-selected", "false");
          });
          clearValue();
          return;
        }
        list.querySelectorAll(".proximity-scroll__entry").forEach((row) => {
          const selected = row === btn;
          row.classList.toggle("is-selected", selected);
          row.setAttribute("aria-selected", selected ? "true" : "false");
        });
        setValue(entry.guess_value);
      });

      list.appendChild(btn);
    });

    if (!entries.length) {
      const empty = document.createElement("p");
      empty.className = "arcade-text-muted proximity-scroll__empty";
      empty.textContent = "No hay capítulos o episodios en este arco.";
      list.appendChild(empty);
    }

    scroll.appendChild(list);
    panelEl.appendChild(scroll);
    triggerOpenAnimation();
  }

  function renderInitialState() {
    if (!bodyEl) return;
    bodyEl.innerHTML = "";

    if (!arcs.length) {
      const empty = document.createElement("p");
      empty.className = "proximity-picker__hint";
      empty.textContent = "No hay arcos en el catálogo del pool.";
      bodyEl.appendChild(empty);
      return;
    }

    showArcPanel();
  }

  if (submitBtn) {
    submitBtn.disabled = true;
  }

  renderInitialState();

  return {
    getValue: () => currentValue,
    setValue: (value) => setValue(value),
    showArcs: showArcPanel,
    getSelectedArc: () => selectedArc,
  };
}

window.initOnePieceScrollPicker = initOnePieceScrollPicker;
