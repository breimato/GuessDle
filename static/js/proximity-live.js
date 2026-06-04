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
  const errorEl = document.getElementById("proximity-guess-error");
  const timerFillEl = document.getElementById("proximity-timer-fill");
  const timerBarEl = document.getElementById("proximity-timer-bar");
  const timerSeconds = parseInt(gameData.dataset.timerSeconds || "60", 10);
  const modalRoot = document.getElementById("proximity-modal-root");
  const playNav = document.querySelector(".play-nav");

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

  function showFinishedModal({ won, answer, score, firstGuess, timedOut }) {
    lockFiltersNav();
    let title;
    if (won) {
      title = "¡HAS ACERTADO!";
    } else if (timedOut) {
      title = `Tiempo agotado.<br><br>Respuesta: ${escapeHtml(answer)}<br>¡Te has quedado a ${escapeHtml(score)}!`;
    } else {
      title = `Respuesta: ${escapeHtml(answer)}<br>Tu intento: ${escapeHtml(firstGuess ?? "?")}<br>¡Te has quedado a ${escapeHtml(score)}!`;
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
    const body = new FormData();
    body.append("csrfmiddlewaretoken", csrf);
    try {
      const data = await postForm(timeoutUrl, body);
      applyState(data);
      showFinishedModal({
        won: false,
        answer: data.answer_value,
        score: data.score_locked,
        timedOut: true,
      });
    } catch (err) {
      timeoutRequested = false;
      if (errorEl) {
        errorEl.textContent = err.message;
        errorEl.classList.remove("hidden");
      }
    }
  }

  function updateTimerBar(pct) {
    if (!timerFillEl) return;
    const clamped = Math.max(0, Math.min(100, pct));
    timerFillEl.style.width = `${clamped}%`;
    if (timerBarEl) {
      timerBarEl.setAttribute("aria-valuenow", String(Math.round(clamped)));
    }
  }

  function startTimerBar() {
    if (!isTeamPlay || !deadlineIso || !timerFillEl || !canPlay) return;
    const deadline = new Date(deadlineIso).getTime();
    const totalMs = timerSeconds * 1000;

    function tick() {
      const remainingMs = deadline - Date.now();
      if (remainingMs <= 0) {
        updateTimerBar(0);
        handleTimeout();
        return;
      }
      updateTimerBar((remainingMs / totalMs) * 100);
    }

    tick();
    timerInterval = setInterval(tick, 250);
  }

  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!canPlay) return;
    errorEl?.classList.add("hidden");
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
    showFinishedModal({
      won: finishedFlag.dataset.won === "true",
      answer: finishedFlag.dataset.answer,
      score: finishedFlag.dataset.score,
      firstGuess: finishedFlag.dataset.firstGuess,
      timedOut: finishedFlag.dataset.timedOut === "true",
    });
  } else {
    startTimerBar();
  }
});
