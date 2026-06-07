document.addEventListener("DOMContentLoaded", () => {
  const gameData = document.getElementById("proximity-game-data");
  if (!gameData) return;

  const guessUrl = gameData.dataset.guessUrl;
  const timeoutUrl = gameData.dataset.timeoutUrl;
  let canPlay = gameData.dataset.canPlay === "true";
  const modesUrl = gameData.dataset.modesUrl || null;
  const panelUrl = gameData.dataset.panelUrl || "/accounts/";
  const isTeamPlay = gameData.dataset.isTeamPlay === "true";
  const deadlineIso = gameData.dataset.deadlineIso || "";
  const csrf = document.querySelector("[name=csrfmiddlewaretoken]")?.value;

  const form = document.getElementById("proximity-guess-form");
  const input = document.getElementById("guess");
  const pickerEl = document.getElementById("proximity-guess-picker");
  const submitBtn = document.getElementById("proximity-guess-submit");
  const errorEl = document.getElementById("proximity-guess-error");
  const timerFillEl = document.getElementById("proximity-timer-fill");
  const timerBarEl = document.getElementById("proximity-timer-bar");
  const timerCountdownEl = document.getElementById("proximity-timer-countdown");
  const timerSeconds = parseInt(gameData.dataset.timerSeconds || "60", 10);
  const TIMER_PHASE_HIGH = 50;
  const TIMER_PHASE_LOW = 25;
  const TIMER_FILL_PHASE_CLASSES = [
    "proximity-timer__fill--high",
    "proximity-timer__fill--mid",
    "proximity-timer__fill--low",
  ];
  const TIMER_COUNTDOWN_PHASE_CLASSES = [
    "proximity-timer__countdown--high",
    "proximity-timer__countdown--mid",
    "proximity-timer__countdown--low",
  ];
  const modalRoot = document.getElementById("proximity-modal-root");
  const playNav = document.querySelector(".play-nav");
  const valueUnit = pickerEl?.dataset.valueUnit || "";

  let timerInterval = null;
  let timeoutRequested = false;

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function isGameFinished(data) {
    if (data) {
      return (
        data.can_play === false
        || data.filters_locked === true
        || (data.answer_value !== null && data.answer_value !== undefined)
      );
    }
    return gameData.dataset.canPlay !== "true" || gameData.dataset.filtersLocked === "true";
  }

  function lockFiltersNav() {
    playNav?.classList.add("play-nav--filters-hidden");
    document.querySelectorAll(".play-nav__filters").forEach((link) => link.remove());
  }

  function showModal(title, actionsHtml = "") {
    if (!modalRoot) return;
    modalRoot.innerHTML = `
      <div class="arcade-modal-overlay">
        <div class="arcade-modal">
          <button type="button" class="arcade-modal__close" data-close-modal aria-label="Cerrar">&times;</button>
          <h2 class="arcade-modal__title">${title}</h2>
          <div class="arcade-modal__actions flex flex-col gap-3 mt-4 w-full max-w-xs">
            ${actionsHtml}
          </div>
        </div>
      </div>`;
    const overlay = modalRoot.querySelector(".arcade-modal-overlay");
    const close = () => { modalRoot.innerHTML = ""; };
    modalRoot.querySelectorAll("[data-close-modal]").forEach((btn) => btn.addEventListener("click", close));
    overlay?.addEventListener("click", (e) => { if (e.target === overlay) close(); });
  }

  const modalNav = window.GuessDlePlayModalNav?.readFromDataset(gameData) ?? {
    modesUrl,
    panelUrl,
  };

  function modalActions() {
    if (window.GuessDlePlayModalNav?.buildActionsHtml) {
      return window.GuessDlePlayModalNav.buildActionsHtml(modalNav);
    }
    const modesLink = modesUrl
      ? `<a href="${modesUrl}" class="arcade-btn arcade-btn--secondary arcade-btn--full">Modos</a>`
      : "";
    return `${modesLink}<a href="${panelUrl}" class="arcade-btn arcade-btn--primary arcade-btn--full">Dashboard</a>`;
  }

  function showFinishedModal({ won, answer, score, firstGuess, timedOut, noAnswer, value_unit: modalValueUnit }) {
    lockFiltersNav();
    const unit = modalValueUnit || valueUnit;
    const formatValue = (value) => {
      if (value === null || value === undefined || value === "") {
        return "?";
      }
      return unit ? `${unit} ${value}` : String(value);
    };
    const answerLabel = formatValue(answer);
    const guessLabel = formatValue(firstGuess);
    let title;
    if (won) {
      title = "¡HAS ACERTADO!";
    } else if (timedOut && noAnswer) {
      title = `No contestaste a tiempo.<br><br>¡Has perdido!<br>Respuesta: ${escapeHtml(answerLabel)}`;
    } else if (timedOut) {
      title = `Tiempo agotado.<br><br>Respuesta: ${escapeHtml(answerLabel)}<br>¡Te has quedado a ${escapeHtml(score)}!`;
    } else {
      title = `Respuesta: ${escapeHtml(answerLabel)}<br>Tu intento: ${escapeHtml(guessLabel)}<br>¡Te has quedado a ${escapeHtml(score)}!`;
    }
    showModal(title, modalActions());
    if (won && typeof confetti === "function") {
      confetti({ particleCount: 120, spread: 80, origin: { y: 0.55 } });
    }
  }

  function disablePlay() {
    canPlay = false;
    form?.querySelectorAll("input,button").forEach((el) => { el.disabled = true; });
    form?.classList.add("opacity-50", "pointer-events-none");
    if (timerInterval) clearInterval(timerInterval);
  }

  function applyState(data) {
    if (isGameFinished(data)) {
      disablePlay();
      lockFiltersNav();
    }
    return data;
  }

  async function postForm(url, body) {
    const response = await fetch(url, {
      method: "POST",
      headers: { "X-CSRFToken": csrf, "X-Requested-With": "XMLHttpRequest" },
      body,
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Error");
    return data;
  }

  async function handleTimeout() {
    if (timeoutRequested || !canPlay) return;
    timeoutRequested = true;
    const pendingGuess = input?.value?.trim();
    const body = new FormData();
    body.append("csrfmiddlewaretoken", csrf);
    if (pendingGuess) {
      body.append("guess", pendingGuess);
    }
    try {
      const data = applyState(await postForm(timeoutUrl, body));
      if (data.timed_out) {
        showFinishedModal({
          won: false,
          answer: data.answer_value,
          score: data.score_locked,
          timedOut: true,
          noAnswer: !pendingGuess,
          value_unit: data.value_unit,
        });
        return;
      }
      if (input) input.value = "";
      showFinishedModal({
        won: data.won,
        answer: data.answer_value,
        score: data.score_locked,
        firstGuess: data.first_guess_value,
        timedOut: false,
        value_unit: data.value_unit,
      });
    } catch (err) {
      timeoutRequested = false;
      if (errorEl) {
        errorEl.textContent = err.message;
        errorEl.classList.remove("hidden");
      }
    }
  }

  function timerPhaseForPct(pct) {
    if (pct > TIMER_PHASE_HIGH) {
      return "high";
    }
    if (pct > TIMER_PHASE_LOW) {
      return "mid";
    }
    return "low";
  }

  function applyTimerPhase(phase) {
    if (!timerFillEl) return;
    TIMER_FILL_PHASE_CLASSES.forEach((className) => {
      timerFillEl.classList.remove(className);
    });
    timerFillEl.classList.add(`proximity-timer__fill--${phase}`);
    if (!timerCountdownEl) return;
    TIMER_COUNTDOWN_PHASE_CLASSES.forEach((className) => {
      timerCountdownEl.classList.remove(className);
    });
    timerCountdownEl.classList.add(`proximity-timer__countdown--${phase}`);
  }

  function formatCountdown(remainingMs) {
    const totalSeconds = Math.max(0, Math.ceil(remainingMs / 1000));
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes}:${String(seconds).padStart(2, "0")}`;
  }

  function updateTimerBar(pct, remainingMs) {
    if (!timerFillEl) return;
    const clamped = Math.max(0, Math.min(100, pct));
    const phase = timerPhaseForPct(clamped);
    timerFillEl.style.width = `${clamped}%`;
    applyTimerPhase(phase);
    if (timerBarEl) {
      timerBarEl.setAttribute("aria-valuenow", String(Math.round(clamped)));
    }
    if (timerCountdownEl && remainingMs !== undefined) {
      timerCountdownEl.textContent = formatCountdown(remainingMs);
    }
  }

  function startTimerBar() {
    if (!isTeamPlay || !deadlineIso || !timerFillEl || !canPlay) return;
    const deadline = new Date(deadlineIso).getTime();
    const totalMs = timerSeconds * 1000;

    function tick() {
      const remainingMs = deadline - Date.now();
      if (remainingMs <= 0) {
        updateTimerBar(0, 0);
        handleTimeout();
        return;
      }
      updateTimerBar((remainingMs / totalMs) * 100, remainingMs);
    }

    tick();
    timerInterval = setInterval(tick, 250);
  }

  if (pickerEl && input && submitBtn && typeof initProximityGuessPicker === "function") {
    initProximityGuessPicker(pickerEl, input, submitBtn);
  }

  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!canPlay) return;
    errorEl?.classList.add("hidden");
    if (!input?.value) {
      if (errorEl) {
        errorEl.textContent = "Elige una respuesta antes de probar.";
        errorEl.classList.remove("hidden");
      }
      return;
    }
    const body = new FormData(form);
    try {
      const data = applyState(await postForm(guessUrl, body));
      input.value = "";
      showFinishedModal({
        won: data.won,
        answer: data.answer_value,
        score: data.score_locked,
        firstGuess: data.first_guess_value,
        timedOut: false,
        value_unit: data.value_unit,
      });
    } catch (err) {
      if (errorEl) {
        errorEl.textContent = err.message;
        errorEl.classList.remove("hidden");
      }
    }
  });

  const infoBtn = document.getElementById("proximity-info-btn");
  const infoOverlay = document.getElementById("proximity-info-modal");
  if (infoBtn && infoOverlay) {
    const closeInfo = () => { infoOverlay.hidden = true; };
    infoBtn.addEventListener("click", () => { infoOverlay.hidden = false; });
    infoOverlay.querySelector("[data-close-proximity-info]")?.addEventListener("click", closeInfo);
    infoOverlay.addEventListener("click", (event) => {
      if (event.target === infoOverlay) closeInfo();
    });
  }

  if (isGameFinished()) {
    lockFiltersNav();
  }

  const finishedFlag = document.getElementById("proximity-finished-flag");
  if (finishedFlag) {
    disablePlay();
    lockFiltersNav();
    const timedOut = finishedFlag.dataset.timedOut === "true";
    const firstGuess = finishedFlag.dataset.firstGuess;
    showFinishedModal({
      won: finishedFlag.dataset.won === "true",
      answer: finishedFlag.dataset.answer,
      score: finishedFlag.dataset.score,
      firstGuess,
      timedOut,
      noAnswer: timedOut && !firstGuess,
    });
  } else {
    startTimerBar();
  }
});
