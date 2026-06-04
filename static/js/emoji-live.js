document.addEventListener("DOMContentLoaded", () => {
  const gameData = document.getElementById("emoji-game-data");
  if (!gameData) return;

  const playMessages = window.GuessDlePlayMessages;
  const guessUrl = gameData.dataset.guessUrl;
  const surrenderUrl = gameData.dataset.surrenderUrl;
  const canPlay = gameData.dataset.canPlay === "true";
  const modesUrl = gameData.dataset.modesUrl || null;
  const panelUrl = gameData.dataset.panelUrl || "/accounts/";
  const csrf = document.querySelector("[name=csrfmiddlewaretoken]")?.value;

  const cluesDisplay = document.getElementById("emoji-clues-display");
  const cluesCountEl = document.getElementById("emoji-clues-count");
  const guessesList = document.getElementById("emoji-guesses-list");
  const form = document.getElementById("emoji-guess-form");
  const input = document.getElementById("guess");
  const errorEl = document.getElementById("emoji-guess-error");
  const surrenderBtn = document.getElementById("emoji-surrender-btn");
  const modalRoot = document.getElementById("emoji-modal-root");

  function injectKeyframes() {
    if (document.getElementById("bounce-modal-style")) return;
    const style = document.createElement("style");
    style.id = "bounce-modal-style";
    style.textContent = `
      @keyframes bounceInCenter{
        0%{opacity:0;transform:scale(.9) translateY(-40px)}
        60%{opacity:1;transform:scale(1.03) translateY(8px)}
        80%{transform:scale(.97) translateY(-4px)}
        100%{transform:scale(1) translateY(0)}
      }
      .animate-bounceInCenter{
        animation:bounceInCenter .75s cubic-bezier(.25,.8,.25,1) forwards;
      }`;
    document.head.appendChild(style);
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function showModal(title, actionsHtml = "") {
    if (!modalRoot) return;
    injectKeyframes();
    modalRoot.innerHTML = `
      <div class="arcade-modal-overlay">
        <div class="arcade-modal animate-bounceInCenter">
          <button type="button" class="arcade-modal__close" data-close-modal aria-label="Cerrar">&times;</button>
          <h2 class="arcade-modal__title">${title}</h2>
          <div class="arcade-modal__actions flex flex-col gap-3 mt-4 w-full max-w-xs">
            ${actionsHtml}
          </div>
        </div>
      </div>`;

    const overlay = modalRoot.querySelector(".arcade-modal-overlay");
    const close = () => { modalRoot.innerHTML = ""; };
    modalRoot.querySelectorAll("[data-close-modal]").forEach((button) => {
      button.addEventListener("click", close);
    });
    overlay?.addEventListener("click", (event) => {
      if (event.target === overlay) close();
    });
  }

  function showEndModal(targetName, outcome) {
    const title = playMessages?.buildModalTitle(outcome, targetName)
      ?? (outcome === "surrender"
        ? `¡Qué lástima! El personaje era ${targetName}`
        : `¡Correcto! ${targetName}`);
    const navOptions = window.GuessDlePlayModalNav?.readFromDataset(gameData) ?? {
      modesUrl,
      panelUrl,
    };
    const actionsHtml = window.GuessDlePlayModalNav?.buildActionsHtml(navOptions)
      ?? `<a href="${panelUrl}" class="arcade-btn arcade-btn--primary arcade-btn--full">Dashboard</a>`;
    showModal(title, actionsHtml);
    if (outcome === "victory") {
      launchConfettiSides();
    }
  }

  function launchConfettiSides() {
    if (typeof confetti !== "function") return;
    const end = Date.now() + 2000;
    (function frame() {
      confetti({ particleCount: 12, angle: 60, spread: 60, origin: { x: 0, y: 0.6 } });
      confetti({ particleCount: 12, angle: 120, spread: 60, origin: { x: 1, y: 0.6 } });
      if (Date.now() < end) requestAnimationFrame(frame);
    })();
  }

  function disablePlayControls() {
    form?.querySelectorAll("input,button").forEach((el) => { el.disabled = true; });
    form?.classList.add("opacity-50", "pointer-events-none");
    surrenderBtn?.remove();
  }

  function showError(message) {
    if (!errorEl) return;
    errorEl.textContent = message;
    errorEl.classList.remove("hidden");
  }

  function clearError() {
    if (!errorEl) return;
    errorEl.textContent = "";
    errorEl.classList.add("hidden");
  }

  function renderClues(clues) {
    if (!cluesDisplay) return;
    cluesDisplay.innerHTML = (clues || [])
      .map((clue) => `<span class="emoji-clues__item">${escapeHtml(clue)}</span>`)
      .join("");
    if (cluesCountEl) cluesCountEl.textContent = String((clues || []).length);
  }

  const DEFAULT_PORTRAIT = gameData.dataset.defaultPortrait || "/static/images/default-character.png";

  function buildGuessCardElement(attempt) {
    const stateClass = attempt.is_correct ? "square-good" : "square-bad";
    const card = document.createElement("div");
    card.className = `emoji-guess-card square ${stateClass}`;
    const imageUrl = attempt.guess_image_url || DEFAULT_PORTRAIT;
    card.innerHTML = `
      <div class="square-content emoji-guess-card__content">
        <img
          src="${escapeHtml(imageUrl)}"
          alt="${escapeHtml(attempt.name)}"
          title="${escapeHtml(attempt.name)}"
          class="guess-portrait emoji-guess-card__portrait"
          onerror="this.onerror=null; this.src='${DEFAULT_PORTRAIT}';">
      </div>`;
    return card;
  }

  function appendGuessCard(attempt, animate = true) {
    if (!guessesList) return;
    const card = buildGuessCardElement(attempt);
    guessesList.prepend(card);
    if (!animate) {
      card.classList.add("show");
      return;
    }
    requestAnimationFrame(() => {
      card.classList.add("show", "animate__animated", "animate__flipInY");
      card.style.setProperty("--animate-duration", "0.9s");
    });
  }

  function updateAutocomplete(remainingNames) {
    if (!input || !remainingNames) return;
    input.dataset.names = JSON.stringify(remainingNames);
  }

  function handleState(state) {
    renderClues(state.revealed_clues);
    updateAutocomplete(state.remaining_names);

    if (state.won) {
      disablePlayControls();
      showEndModal(state.target_name, "victory");
      return;
    }

    if (state.surrendered) {
      disablePlayControls();
      showEndModal(state.target_name, "surrender");
    }
  }

  async function postAction(url, body = new URLSearchParams()) {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "X-CSRFToken": csrf,
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body,
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Error en la partida.");
    }
    return data;
  }

  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!canPlay) return;
    clearError();
    const guess = input?.value.trim();
    if (!guess) return;

    try {
      const state = await postAction(guessUrl, new URLSearchParams({ guess }));
      form.reset();
      const lastAttempt = state.attempts?.[state.attempts.length - 1];
      if (lastAttempt) {
        appendGuessCard(lastAttempt, true);
      }
      handleState(state);
    } catch (error) {
      showError(error.message);
    }
  });

  surrenderBtn?.addEventListener("click", async () => {
    if (!canPlay || !surrenderUrl) return;
    const confirmed = window.confirm("¿Seguro que quieres rendirte? Se revelará la respuesta.");
    if (!confirmed) return;

    try {
      const state = await postAction(surrenderUrl, new URLSearchParams({ csrfmiddlewaretoken: csrf }));
      disablePlayControls();
      showEndModal(state.target_name, "surrender");
    } catch (error) {
      showError(error.message);
    }
  });

  const wonFlag = document.getElementById("emoji-won-flag");
  if (wonFlag) {
    disablePlayControls();
    setTimeout(() => showEndModal(wonFlag.dataset.champ, "victory"), 200);
  }

  const surrenderFlag = document.getElementById("emoji-surrender-flag");
  if (surrenderFlag) {
    disablePlayControls();
    setTimeout(() => showEndModal(surrenderFlag.dataset.champ, "surrender"), 200);
  }
});
