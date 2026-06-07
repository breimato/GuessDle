/**
 * Proximity guess picker router and numeric fallback picker.
 */

function initNumericProximityPicker(pickerEl, hiddenInput, submitBtn) {
  if (!pickerEl || !hiddenInput) return null;

  const mode = pickerEl.dataset.pickerMode || "slider";
  const min = parseInt(pickerEl.dataset.guessMin || "1", 10);
  const max = parseInt(pickerEl.dataset.guessMax || "1", 10);
  const step = parseInt(pickerEl.dataset.guessStep || "1", 10);
  const blockSize = parseInt(pickerEl.dataset.segmentBlockSize || "100", 10);
  const unit = pickerEl.dataset.valueUnit || "";

  let discreteValues = null;
  const discreteScript = document.getElementById("proximity-discrete-values");
  if (discreteScript?.textContent) {
    try {
      discreteValues = JSON.parse(discreteScript.textContent);
    } catch {
      discreteValues = null;
    }
  }

  let currentValue = null;
  let segmentedBlock = null;

  const displayEl = pickerEl.querySelector(".proximity-picker__value");
  const bodyEl = pickerEl.querySelector(".proximity-picker__body");

  function clamp(value) {
    return Math.max(min, Math.min(max, value));
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
    currentValue = clamp(value);
    hiddenInput.value = String(currentValue);
    if (displayEl) {
      displayEl.textContent = String(currentValue);
    }
    if (submitBtn) {
      submitBtn.disabled = false;
    }
    pickerEl.dispatchEvent(
      new CustomEvent("proximity-guess-change", { detail: { value: currentValue } })
    );
  }

  function clearBody() {
    if (bodyEl) bodyEl.innerHTML = "";
  }

  function renderDiscrete() {
    clearBody();
    const values = Array.isArray(discreteValues) && discreteValues.length
      ? discreteValues
      : rangeList(min, max, step);
    const grid = document.createElement("div");
    grid.className = "proximity-picker__grid";
    values.forEach((val) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "proximity-picker__chip";
      btn.textContent = String(val);
      btn.dataset.value = String(val);
      btn.addEventListener("click", () => {
        if (currentValue === val) {
          grid.querySelectorAll(".proximity-picker__chip").forEach((chip) => {
            chip.classList.remove("is-selected");
            chip.setAttribute("aria-pressed", "false");
          });
          clearValue();
          return;
        }
        grid.querySelectorAll(".proximity-picker__chip").forEach((chip) => {
          const selected = chip === btn;
          chip.classList.toggle("is-selected", selected);
          chip.setAttribute("aria-pressed", selected ? "true" : "false");
        });
        setValue(val);
      });
      grid.appendChild(btn);
    });
    bodyEl.appendChild(grid);
  }

  function buildSliderControls(rangeMin, rangeMax, initial) {
    const wrap = document.createElement("div");
    wrap.className = "proximity-picker__slider-wrap";

    const slider = document.createElement("input");
    slider.type = "range";
    slider.className = "proximity-picker__slider";
    slider.min = String(rangeMin);
    slider.max = String(rangeMax);
    slider.step = String(step);
    const start = initial ?? Math.round((rangeMin + rangeMax) / 2);
    slider.value = String(start);
    slider.addEventListener("input", () => setValue(parseInt(slider.value, 10)));

    const stepper = document.createElement("div");
    stepper.className = "proximity-picker__stepper";
    const minus = document.createElement("button");
    minus.type = "button";
    minus.className = "proximity-picker__step-btn";
    minus.textContent = "−";
    const plus = document.createElement("button");
    plus.type = "button";
    plus.className = "proximity-picker__step-btn";
    plus.textContent = "+";
    minus.addEventListener("click", () => {
      slider.value = String(clamp(parseInt(slider.value, 10) - step));
      setValue(parseInt(slider.value, 10));
    });
    plus.addEventListener("click", () => {
      slider.value = String(clamp(parseInt(slider.value, 10) + step));
      setValue(parseInt(slider.value, 10));
    });
    stepper.append(minus, plus);
    wrap.append(slider, stepper);
    setValue(parseInt(slider.value, 10));
    return wrap;
  }

  function renderSlider(initial) {
    clearBody();
    bodyEl.appendChild(buildSliderControls(min, max, initial));
  }

  function blockStarts() {
    const starts = [];
    let start = min;
    while (start <= max) {
      starts.push(start);
      start += blockSize;
    }
    return starts;
  }

  function renderSegmentBlocks() {
    clearBody();
    segmentedBlock = null;
    const label = document.createElement("p");
    label.className = "proximity-picker__hint";
    label.textContent = `Elige un tramo de ${unit || "valores"}`.trim();
    const grid = document.createElement("div");
    grid.className = "proximity-picker__grid proximity-picker__grid--segments";
    blockStarts().forEach((blockMin) => {
      const blockMax = Math.min(blockMin + blockSize - 1, max);
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "proximity-picker__chip proximity-picker__chip--segment";
      btn.textContent = `${blockMin} – ${blockMax}`;
      btn.addEventListener("click", () => {
        segmentedBlock = { min: blockMin, max: blockMax };
        renderSegmentFine();
      });
      grid.appendChild(btn);
    });
    bodyEl.append(label, grid);
  }

  function renderSegmentFine() {
    if (!segmentedBlock) return;
    clearBody();
    const back = document.createElement("button");
    back.type = "button";
    back.className = "proximity-picker__back arcade-btn arcade-btn--secondary";
    back.textContent = "← Cambiar tramo";
    back.addEventListener("click", renderSegmentBlocks);

    const hint = document.createElement("p");
    hint.className = "proximity-picker__hint";
    hint.textContent = `${segmentedBlock.min} – ${segmentedBlock.max}`;

    const mid = Math.round((segmentedBlock.min + segmentedBlock.max) / 2);
    const sliderWrap = buildSliderControls(segmentedBlock.min, segmentedBlock.max, mid);
    bodyEl.append(back, hint, sliderWrap);
  }

  function rangeList(from, to, stride) {
    const items = [];
    for (let v = from; v <= to; v += stride) {
      items.push(v);
    }
    return items;
  }

  if (submitBtn) {
    submitBtn.disabled = mode !== "slider";
  }

  if (mode === "discrete") {
    renderDiscrete();
  } else if (mode === "slider") {
    renderSlider();
  } else {
    renderSegmentBlocks();
  }

  return { getValue: () => currentValue, setValue };
}

function initProximityGuessPicker(pickerEl, hiddenInput, submitBtn) {
  if (!pickerEl || !hiddenInput) return null;

  const mode = pickerEl.dataset.pickerMode || "slider";

  if (mode === "pokemon_pokedex" && typeof initPokemonPokedexPicker === "function") {
    return initPokemonPokedexPicker(pickerEl, hiddenInput, submitBtn);
  }
  if (
    mode === "lol_champions"
    && (typeof initLolYearsPicker === "function" || typeof initLolChampionsPicker === "function")
  ) {
    const initLol = typeof initLolYearsPicker === "function"
      ? initLolYearsPicker
      : initLolChampionsPicker;
    return initLol(pickerEl, hiddenInput, submitBtn);
  }
  if (mode === "one_piece_scroll" && typeof initOnePieceScrollPicker === "function") {
    return initOnePieceScrollPicker(pickerEl, hiddenInput, submitBtn);
  }

  return initNumericProximityPicker(pickerEl, hiddenInput, submitBtn);
}

window.initProximityGuessPicker = initProximityGuessPicker;
window.initNumericProximityPicker = initNumericProximityPicker;
