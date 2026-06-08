document.addEventListener("DOMContentLoaded", () => {
  const playMessages = window.GuessDlePlayMessages;
  const formatEloAmount = (amount) => playMessages.formatEloAmount(amount);

  /* ───────── nodos básicos ───────── */
  const cont = document.getElementById("attempts-container");
  const header = document.getElementById("attempts-header");
  const form = document.getElementById("guess-form");
  const csrf = document.querySelector("[name=csrfmiddlewaretoken]")?.value;
  const gameData = document.getElementById("game-data");
  const slug = gameData?.dataset.slug;
  const extraId = gameData?.dataset.extraId;
  const modeMatch = location.pathname.match(/\/play\/[^/]+\/([^/]+)\/?$/);
  const modeSlug = gameData?.dataset.modeSlug || modeMatch?.[1];
  const startExtraURL = gameData?.dataset.startExtraUrl
    || (slug
      ? (modeSlug ? `/games/start-extra/${slug}/${modeSlug}/` : `/games/start-extra/${slug}/`)
      : null);
  let maxExtrasReached = gameData?.dataset.maxExtrasReached === "true";

  function syncMaxExtrasReached(value) {
    if (typeof value !== "boolean") return;
    maxExtrasReached = value;
    if (gameData) {
      gameData.dataset.maxExtrasReached = value ? "true" : "false";
    }
  }
  const modesUrl = gameData?.dataset.modesUrl || null;
  const panelUrl = gameData?.dataset.panelUrl || "/accounts/";
  const surrenderUrl = gameData?.dataset.surrenderUrl || null;

  function hideSurrenderButton() {
    document.getElementById("surrender-btn")?.remove();
  }

  const surrenderBtn = document.getElementById("surrender-btn");




  /* ────── gap y columnas (anchas solo si hace falta) ────── */
  const DEFAULT_CELL = 110;
  const MAX_WIDE_CELL = 300;
  const CELL_PAD = 38;
  const BOARD_FONT = "600 0.875rem Rubik, sans-serif";

  let columnWidths = null;
  let measureEl = null;

  function getMeasureEl() {
    if (!measureEl) {
      measureEl = document.createElement("span");
      measureEl.className = "square-text board-measure-probe";
      measureEl.setAttribute("aria-hidden", "true");
      Object.assign(measureEl.style, {
        position: "absolute",
        visibility: "hidden",
        whiteSpace: "nowrap",
        pointerEvents: "none",
        left: "-9999px",
        top: "0",
        font: BOARD_FONT,
      });
      document.body.appendChild(measureEl);
    }
    return measureEl;
  }

  function measureText(text) {
    const el = getMeasureEl();
    el.textContent = String(text ?? "");
    return el.getBoundingClientRect().width;
  }

  function stripArrow(text) {
    return String(text ?? "").replace(/[▲▼]/g, "").trim();
  }

  function isSingleToken(text) {
    const clean = stripArrow(text);
    return Boolean(clean) && !/\s/.test(clean);
  }

  function widthForCellValue(text) {
    const display = String(text ?? "").trim();
    if (!isSingleToken(display)) return DEFAULT_CELL;

    const needed = Math.ceil(measureText(display) + CELL_PAD);
    if (needed <= DEFAULT_CELL) return DEFAULT_CELL;
    return Math.min(MAX_WIDE_CELL, needed);
  }

  function getFeedbackCount() {
    const firstRow = cont?.querySelector(".attempt-row");
    if (firstRow) return firstRow.querySelectorAll(".square").length - 1;
    const cols = parseInt(header?.dataset.cols, 10);
    return Number.isFinite(cols) && cols > 1 ? cols - 1 : 0;
  }

  function ensureColumnWidths(colCount) {
    if (!columnWidths || columnWidths.length !== colCount) {
      columnWidths = new Array(colCount).fill(DEFAULT_CELL);
    }
    return columnWidths;
  }

  function rebuildColumnWidthsFromDom(feedbackCount) {
    const widths = ensureColumnWidths(feedbackCount + 1);
    widths.fill(DEFAULT_CELL);

    document.querySelectorAll(".attempt-row").forEach(row => {
      row.querySelectorAll(".square").forEach((cell, idx) => {
        if (idx === 0) return;
        widths[idx] = Math.max(widths[idx], widthForCellValue(cell.textContent || ""));
      });
    });

    return widths;
  }

  function buildGridTemplate(feedbackCount) {
    const widths = rebuildColumnWidthsFromDom(feedbackCount);
    return widths.map(w => `${w}px`).join(" ");
  }

  function applyBoardGrid(feedbackCount) {
    const template = buildGridTemplate(feedbackCount);
    const gap = calcGap(feedbackCount + 1);
    if (header) {
      header.style.gridTemplateColumns = template;
      header.style.gap = gap;
    }
    document.querySelectorAll(".attempt-row").forEach(row => {
      row.style.gridTemplateColumns = template;
      row.style.gap = gap;
    });
    return { template, gap };
  }

  /* ────── pistas de columna ────── */
  const hintControlsEl = document.getElementById("hint-controls");
  const hintUseBtn = document.getElementById("hint-use-btn");
  const hintMessagesEl = document.getElementById("hint-messages");
  const revealHintUrl = gameData?.dataset.revealUrl || "";
  let currentHintState = null;

  function loadInitialHintState() {
    const el = document.getElementById("hint-state-data");
    if (!el) return null;
    try {
      return JSON.parse(el.textContent);
    } catch (e) {
      console.error("Hint state parse:", e);
      return null;
    }
  }

  function formatHintValue(value) {
    if (value == null || value === "") return "—";
    if (Array.isArray(value)) return value.map(String).join(", ");
    if (typeof value === "object") return JSON.stringify(value);
    return String(value);
  }

  function normalizeDisplayText(text) {
    if (text == null) return "";
    return String(text).replace(/\\u([0-9a-fA-F]{4})/g, (_, hex) =>
      String.fromCodePoint(parseInt(hex, 16))
    );
  }

  function formatColumnLabel(attribute, label) {
    if (label) return label;
    return String(attribute).replace(/_/g, " ");
  }

  function renderHintMessages(hintState) {
    if (!hintMessagesEl || !hintState?.enabled) return;

    const items = hintState.revealed_hints || [];
    if (!items.length) {
      hintMessagesEl.innerHTML = "";
      hintMessagesEl.classList.add("hidden");
      return;
    }

    hintMessagesEl.innerHTML = items.map(entry => {
      const label = formatColumnLabel(entry.attribute, entry.label).toLocaleUpperCase("es");
      const value = formatHintValue(entry.value).toLocaleUpperCase("es");
      return `<p class="hint-message"><strong>${label}:</strong> ${value}</p>`;
    }).join("");
    hintMessagesEl.classList.remove("hidden");
  }

  function syncHintControls(hintState) {
    if (!hintControlsEl || !hintState?.enabled) {
      hintControlsEl?.classList.add("hidden");
      return;
    }

    const pending = hintState.slots_pending || 0;
    const pickable = hintState.eligible_columns || [];
    const canUseHint = pending > 0 && pickable.length > 0;

    if (canUseHint) {
      hintControlsEl.classList.remove("hidden");
      const label = pending === 1 ? "1 pista disponible" : `${pending} pistas disponibles`;
      if (hintUseBtn) {
        hintUseBtn.textContent = `Revelar pista (${label})`;
        hintUseBtn.disabled = false;
      }
    } else {
      hintControlsEl.classList.add("hidden");
    }
  }

  async function postRevealHint(attribute) {
    if (!revealHintUrl) throw new Error("Reveal URL no configurada.");
    const body = new URLSearchParams({ attribute });
    const res = await fetch(revealHintUrl, {
      method: "POST",
      headers: {
        "X-CSRFToken": csrf,
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Error al revelar pista.");
    return data.hint_state;
  }

  function handleHintState(hintState) {
    if (!hintState?.enabled) return;
    currentHintState = hintState;
    renderHintMessages(hintState);
    syncHintControls(hintState);
  }

  hintUseBtn?.addEventListener("click", async () => {
    if (!currentHintState) return;
    const pickable = currentHintState.eligible_columns || [];
    if (!pickable.length) return;

    hintUseBtn.disabled = true;
    try {
      const nextState = await postRevealHint(pickable[0].attribute);
      handleHintState(nextState);
    } catch (err) {
      showErrorModal(err.message || "Error");
      hintUseBtn.disabled = false;
    }
  });

  currentHintState = loadInitialHintState();
  if (currentHintState) {
    handleHintState(currentHintState);
  }

  function calcGap(cols) {
    if (cols <= 4) return "10px";
    if (cols <= 6) return "8px";
    if (cols <= 8) return "6px";
    if (cols <= 10) return "4px";
    return "2px";
  }

  /* ───────── 1· historial ───────── */
  const initJSON = document.getElementById("initial-attempts");
  if (initJSON) {
    try {
      JSON.parse(initJSON.textContent)
        .reverse()
        .forEach(a => renderAttempt(a, false));
      document.fonts?.ready?.then(() => applyBoardGrid(getFeedbackCount()));
    } catch (e) { console.error("Historial parse:", e); }
  }

  const betDataEl = document.getElementById("bet-tracking-data");
  let betData = null;
  if (betDataEl) {
    try {
      betData = JSON.parse(betDataEl.textContent);
    } catch (e) {
      console.error("Error parsing bet tracking data:", e);
    }
  }

  function buildBetInfoFromResponse(data) {
    if (!data || data.bet_amount == null) return null;
    const betAmount = Number(data.bet_amount);
    const betWon = data.bet_won === true || data.bet_won === "true";
    const netProfit = data.net_profit != null
      ? Number(data.net_profit)
      : Math.max(0, Number(data.points_awarded || 0) - betAmount);
    return { betAmount, betWon, netProfit };
  }

  function mergeBetResponse(data) {
    if (!betData || !data) return;
    if (data.bet_amount != null) betData.bet_amount = Number(data.bet_amount);
    if (data.global_average != null) betData.global_average = data.global_average;
  }

  const normalizeChallengeData = (data) => playMessages.normalizeChallengeData(data);

  async function fetchChallengeReport(attempts) {
    const reportUrl = typeof CHALLENGE_REPORT_URL !== "undefined" ? CHALLENGE_REPORT_URL : "";
    const token = typeof CSRF_TOKEN !== "undefined" ? CSRF_TOKEN : csrf;
    if (!reportUrl) return null;
    const challengeRes = await fetch(reportUrl, {
      method: "POST",
      headers: {
        "X-CSRFToken": token,
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded"
      },
      body: new URLSearchParams({ attempts })
    });
    if (!challengeRes.ok) return null;
    return normalizeChallengeData(await challengeRes.json());
  }

  function updateChallengeModalSection(overlay, challengeData) {
    const slot = overlay?.querySelector("[data-challenge-message]");
    if (!slot) return;
    const html = playMessages.buildChallengeMessageHtml(challengeData);
    slot.innerHTML = html || '<p class="arcade-msg--wait">No se pudo cargar el resultado del reto.</p>';
  }

  async function completeVictoryFlow(targetName, isExtra, betInfo) {
    hideSurrenderButton();
    const isChallenge = typeof IS_CHALLENGE !== "undefined" && IS_CHALLENGE === "true";
    const overlay = showGameEndModal({
      targetName,
      outcome: "victory",
      isExtra,
      betInfo,
      challengeData: null,
      challengePending: isChallenge,
    });
    if (!isChallenge) return;
    const attemptsPlayed = document.querySelectorAll("#attempts-container > *").length;
    try {
      const challengeData = await fetchChallengeReport(attemptsPlayed);
      updateChallengeModalSection(overlay, challengeData);
    } catch (err) {
      console.error("Challenge report failed:", err);
    }
  }

  /* ───────── 2· ya ganado previamente ───────── */
  const flag = document.getElementById("won-flag");
  if (flag) {
    disableForm();
    hideSurrenderButton();
    setTimeout(() => {
      const isExtra = flag.dataset.isExtra === "true";
      const betInfo = isExtra ? buildBetInfoFromDataset(flag.dataset) : null;
      void completeVictoryFlow(normalizeDisplayText(flag.dataset.champ), isExtra, betInfo);
    }, 200);
  }

  const surrenderFlag = document.getElementById("surrender-flag");
  if (surrenderFlag) {
    disableForm();
    hideSurrenderButton();
    setTimeout(() => {
      const isExtra = surrenderFlag.dataset.isExtra === "true";
      const betInfo = isExtra ? buildBetInfoFromDataset(surrenderFlag.dataset) : null;
      handleSurrenderCompletion(normalizeDisplayText(surrenderFlag.dataset.champ), isExtra, betInfo);
    }, 200);
  }

  surrenderBtn?.addEventListener("click", submitSurrender);

  /* ───────── 3· envío normal ───────── */
  form?.addEventListener("submit", async e => {
    e.preventDefault();
    const res = await fetch(form.action, {
      method: "POST",
      headers: { "X-CSRFToken": csrf, "X-Requested-With": "XMLHttpRequest" },
      body: new FormData(form)
    });

    const data = await res.json();
    if (!res.ok) { showErrorModal(data.error || "Error"); return; }

    form.reset();
    const row = renderAttempt(data.attempt, true);

    // 🔁 actualizar lista de sugerencias
    const guessInput = document.getElementById("guess");
    if (guessInput && data.remaining_names) {
      guessInput.dataset.names = JSON.stringify(data.remaining_names);
    }

    const betInfo = extraId ? buildBetInfoFromResponse(data) : null;
    if (betData) {
      mergeBetResponse(data);
    }
    syncMaxExtrasReached(data.max_extras_reached);

    if (data.hint_state) {
      handleHintState(data.hint_state);
    }

    if (data.won) {
      hideSurrenderButton();
      const cells = row.querySelectorAll(".square");
      const last = cells[cells.length - 1];
      const runCompletion = () => {
        hideSurrenderButton();
        disableForm();
        void completeVictoryFlow(normalizeDisplayText(data.attempt.name), !!extraId, betInfo);
      };
      if (last) {
        last.addEventListener("animationend", runCompletion, { once: true });
      } else {
        setTimeout(runCompletion, 500);
      }
    }
  });

  function capitalize(text) {
    const normalized = normalizeDisplayText(text);
    return normalized.replace(/(^|\s|-|_)([a-z])/g, (_, sep, char) => sep + char.toUpperCase());
  }

  function wrapCellText(html) {
    const single = isSingleToken(html);
    const cls = single ? "square-text square-text--single" : "square-text";
    return `<span class="${cls}">${html}</span>`;
  }

  /* ───────── render intento ───────── */
  function renderAttempt({ name, icon, feedback, guess_image_url }, animate = true) {
    const row = document.createElement("div");
    row.className = "attempt-row";
    row.style.display = "grid";
    const displayName = normalizeDisplayText(name);

    // Lógica para la celda del personaje/ítem
    let characterCellHtml = "";
    if (guess_image_url) {
      characterCellHtml = `
        <img
          src="${guess_image_url}"
          alt="${capitalize(displayName)}"
          title="${capitalize(displayName)}"
          class="guess-portrait"
          onerror="this.onerror=null; this.src='/static/images/default-character.png';"
        >
      `;
    } else {
      characterCellHtml = `<span class="champion-icon-name">${displayName}</span>`;
    }

    row.append(makeCell({
      isStatic: true,
      html: characterCellHtml
    }));

    feedback.forEach(fb => row.append(makeCell({
      state: fb, html: wrapCellText(`${fb.value ?? ""}${fb.arrow || ""}`)
    })));

    cont.prepend(row);
    applyBoardGrid(feedback.length);

    if (header) {
      header.classList.remove("hidden");
      header.style.display = "grid";
    }

    /* animación flip */
    const cells = row.querySelectorAll(".square");
    if (animate) {
      cells.forEach((c, i) => setTimeout(() => {
        c.classList.add("show", "animate__animated", "animate__flipInY");
        c.style.setProperty("--animate-duration", "0.9s");
      }, i * 500));
    } else cells.forEach(c => c.classList.add("show"));
    return row;
  }

  /* ───────── helpers de estado / celda ───────── */
  function mapState(fb) {
    if (fb.correct) return "good";
    if (fb.partial) return "part";
    if (fb.superior) return "superior";
    return "bad";
  }

  function makeCell({ isStatic = false, state = null, html = "" }) {
    const d = document.createElement("div");
    d.className = "square" + (isStatic ? " square--static" : "") + (state ? " square-" + mapState(state) : "");
    d.innerHTML = `<div class="square-content">${html}</div>`;
    return d;
  }

  /* ───────── deshabilitar formulario ───────── */
  function disableForm() {
    form?.querySelectorAll("input,button").forEach(el => el.disabled = true);
    form?.classList.add("opacity-50", "pointer-events-none");
  }

  function buildBetInfoFromDataset(dataset) {
    return {
      betAmount: parseFloat(dataset.betAmount || "0"),
      betWon: dataset.betWon === "true",
      netProfit: parseFloat(dataset.netProfit || "0"),
    };
  }

  function showErrorModal(message, title = "Error") {
    const overlay = document.createElement("div");
    overlay.className = "arcade-modal-overlay";

    const modal = document.createElement("div");
    modal.className = "arcade-modal";
    const titleClass = title === "Error"
      ? "arcade-modal__title arcade-modal__title--error"
      : "arcade-modal__title arcade-modal__title--confirm";
    modal.innerHTML = `
      <button type="button" class="arcade-modal__close" aria-label="Cerrar">&times;</button>
      <h2 class="${titleClass}">${title}</h2>
      <p class="arcade-modal__message">${message}</p>
      <div class="arcade-modal__actions">
        <button type="button" class="arcade-btn arcade-btn--primary arcade-btn--full">Aceptar</button>
      </div>
    `;

    overlay.appendChild(modal);
    document.body.appendChild(overlay);
    window.GuessDleArcadeModal?.mount(overlay);

    const close = () => overlay.remove();
    modal.querySelector(".arcade-modal__close")?.addEventListener("click", close);
    modal.querySelector(".arcade-btn")?.addEventListener("click", close);
    overlay.addEventListener("click", (event) => {
      if (event.target === overlay) {
        close();
      }
    });
  }

  function bindBetFormSubmit(form) {
    if (!form || !startExtraURL) return;

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const body = new URLSearchParams(new FormData(form));
      if (extraId && !body.get("return_extra_id")) {
        body.set("return_extra_id", extraId);
      }

      const response = await fetch(form.action, {
        method: "POST",
        headers: {
          "X-CSRFToken": csrf,
          "X-Requested-With": "XMLHttpRequest",
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body,
      });
      const data = await response.json();

      if (data.status === "ok" && data.redirect_url) {
        window.location.href = data.redirect_url;
        return;
      }

      if (data.message) {
        showErrorModal(data.message, "Error");
      }
    });
  }

  function showSurrenderConfirmModal() {
    return new Promise((resolve) => {
      const overlay = document.createElement("div");
      overlay.className = "arcade-modal-overlay";
      overlay.setAttribute("role", "dialog");
      overlay.setAttribute("aria-modal", "true");
      overlay.setAttribute("aria-labelledby", "surrender-confirm-title");

      const modal = document.createElement("div");
      modal.className = "arcade-modal";
      modal.innerHTML = `
        <button type="button" class="arcade-modal__close" data-surrender-dismiss aria-label="Cerrar">&times;</button>
        <h2 id="surrender-confirm-title" class="arcade-modal__title arcade-modal__title--confirm">¿Rendirse?</h2>
        <p class="arcade-modal__message">
          Se revelará la respuesta. Tus intentos contarán en el ranking, pero no sumará como partida ganada.
        </p>
        <div class="arcade-modal__actions">
          <button type="button" class="arcade-btn arcade-btn--secondary arcade-btn--full" data-surrender-dismiss>
            Seguir jugando
          </button>
          <button type="button" class="arcade-btn arcade-btn--surrender arcade-btn--full" data-surrender-confirm>
            Sí, rendirme
          </button>
        </div>
      `;

      const closeConfirmModal = (confirmed) => {
        overlay.remove();
        resolve(confirmed);
      };

      overlay.appendChild(modal);
      document.body.appendChild(overlay);
      window.GuessDleArcadeModal?.mount(overlay);

      modal.querySelectorAll("[data-surrender-dismiss]").forEach((button) => {
        button.addEventListener("click", () => closeConfirmModal(false));
      });

      modal.querySelector("[data-surrender-confirm]")?.addEventListener("click", () => {
        closeConfirmModal(true);
      });

      overlay.addEventListener("click", (event) => {
        if (event.target !== overlay) return;
        closeConfirmModal(false);
      });
    });
  }

  async function submitSurrender() {
    if (!surrenderUrl) return;

    const confirmed = await showSurrenderConfirmModal();
    if (!confirmed) return;

    const response = await fetch(surrenderUrl, {
      method: "POST",
      headers: {
        "X-CSRFToken": csrf,
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: new URLSearchParams({ csrfmiddlewaretoken: csrf }),
    });

    const data = await response.json();
    if (!response.ok) {
      showErrorModal(data.error || "Error");
      return;
    }

    disableForm();
    hideSurrenderButton();

    const betInfo = extraId ? buildBetInfoFromResponse(data) : null;
    if (betData) {
      mergeBetResponse(data);
    }
    syncMaxExtrasReached(data.max_extras_reached);

    const challengeData = data.challenge ? normalizeChallengeData(data.challenge) : null;
    handleSurrenderCompletion(
      normalizeDisplayText(data.target_name),
      Boolean(extraId),
      betInfo,
      challengeData,
    );
  }

  function handleGameCompletion(targetName, isExtra, betInfo = null, challengeData = null) {
    return showGameEndModal({
      targetName,
      outcome: "victory",
      isExtra,
      betInfo,
      challengeData,
    });
  }

  function handleSurrenderCompletion(targetName, isExtra, betInfo = null, challengeData = null) {
    hideSurrenderButton();
    showGameEndModal({
      targetName,
      outcome: "surrender",
      isExtra,
      betInfo,
      challengeData,
    });
  }

  function showGameEndModal({
    targetName,
    outcome,
    isExtra = false,
    betInfo = null,
    challengeData = null,
    challengePending = false,
  }) {
  hideSurrenderButton();
  const displayName = normalizeDisplayText(targetName);

  const overlay = document.createElement("div");
  overlay.className = "arcade-modal-overlay";

  const modal = document.createElement("div");
  modal.className = "arcade-modal";

  const betMessageHtml = isExtra && betInfo ? playMessages.buildBetMessageHtml(betInfo) : "";
  const isChallengeModal = typeof IS_CHALLENGE !== "undefined" && IS_CHALLENGE === "true";
  let challengeMessageHtml = "";
  if (isChallengeModal) {
    if (challengePending && !challengeData) {
      challengeMessageHtml = '<p class="arcade-msg--wait">Cargando resultado del reto…</p>';
    } else {
      challengeMessageHtml = playMessages.buildChallengeMessageHtml(challengeData);
    }
  }
  const challengeSectionHtml = isChallengeModal
    ? `<div data-challenge-message>${challengeMessageHtml}</div>`
    : "";

  const extraSectionHtml = !isChallengeModal
    ? (maxExtrasReached
      ? `<div class="arcade-alert arcade-alert--error text-center">Ya has jugado tus 2 partidas extra hoy.</div>`
      : startExtraURL
        ? `<div id="extra-play-wrapper" class="flex flex-col gap-2 w-full">
        <button id="show-bet-form" class="arcade-btn arcade-btn--primary arcade-btn--full">Apostar y jugar extra</button>
        <form method="post" action="${startExtraURL}" id="bet-form" class="flex flex-col gap-2 hidden">
          <input type="hidden" name="csrfmiddlewaretoken" value="${csrf}">
          ${extraId ? `<input type="hidden" name="return_extra_id" value="${extraId}">` : ""}
          <label for="bet" class="arcade-label">¿Cuánto quieres apostar?</label>
          <input type="number" name="bet" min="10" step="1" required class="arcade-input" />
          <button type="submit" class="arcade-btn arcade-btn--primary arcade-btn--full">¡Jugar ahora!</button>
        </form>
      </div>`
        : "")
    : "";

  const modesLinkHtml = modesUrl
    ? `<a href="${modesUrl}" class="arcade-btn arcade-btn--secondary arcade-btn--full">Cambiar modo</a>`
    : "";

  const navigationHtml = isChallengeModal
    ? `<a href="${panelUrl}" class="arcade-btn arcade-btn--primary arcade-btn--full">Dashboard</a>`
    : (window.GuessDlePlayModalNav?.buildActionsHtml(
        window.GuessDlePlayModalNav?.readFromDataset(gameData) ?? { modesUrl, panelUrl }
      ) ?? `<a href="${panelUrl}" class="arcade-btn arcade-btn--primary arcade-btn--full">Dashboard</a>`);

  modal.innerHTML = `
  <button id="close-modal-btn" class="arcade-modal__close">&times;</button>
  <h2 class="arcade-modal__title">${playMessages.buildModalTitle(outcome, displayName)}</h2>
  ${challengeSectionHtml}
  ${betMessageHtml}
  <div class="flex flex-col gap-3 mt-4 w-full max-w-xs">
    ${extraSectionHtml}
    ${isChallengeModal ? modesLinkHtml : ""}
    ${navigationHtml}
  </div>`;


  overlay.appendChild(modal);
  document.body.appendChild(overlay);
  window.GuessDleArcadeModal?.mount(overlay);


  // Event listener para cerrar el modal al hacer click fuera
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) {
      document.body.removeChild(overlay);
    }
  });

  // Event listener para el botón de cierre "X"
  const closeModalBtn = document.getElementById("close-modal-btn");
  if (closeModalBtn) {
    closeModalBtn.addEventListener("click", () => {
      document.body.removeChild(overlay);
    });
  }

  // ✅ Poner aquí el event listener porque los elementos ya existen
  const showBetFormBtn = document.getElementById("show-bet-form");
  const betForm = document.getElementById("bet-form");

  if (showBetFormBtn && betForm) {
    showBetFormBtn.addEventListener("click", () => {
      showBetFormBtn.style.display = "none";
      betForm.classList.remove("hidden");
    });
    bindBetFormSubmit(betForm);
  }

  if (outcome === "victory") {
    launchConfettiSides();
  }

  return overlay;
}


  /* ───────── confetti lados ───────── */
  function launchConfettiSides() {
    const end = Date.now() + 2000;
    (function frame() {
      confetti({ particleCount: 12, angle: 60, spread: 60, origin: { x: 0, y: .6 } });
      confetti({ particleCount: 12, angle: 120, spread: 60, origin: { x: 1, y: .6 } });
      if (Date.now() < end) requestAnimationFrame(frame);
    })();
  }

});
