document.addEventListener("DOMContentLoaded", () => {
  const gameData = document.getElementById("rosco-game-data");
  if (!gameData) return;

  const playMessages = window.GuessDlePlayMessages;
  const answerUrl = gameData.dataset.answerUrl;
  const passUrl = gameData.dataset.passUrl;
  const surrenderUrl = gameData.dataset.surrenderUrl;
  const canPlay = gameData.dataset.canPlay === "true";
  const csrf = document.querySelector("[name=csrfmiddlewaretoken]")?.value;

  const wheel = document.getElementById("rosco-wheel");
  const promptEl = document.getElementById("rosco-prompt");
  const currentLetterEl = document.getElementById("rosco-current-letter");
  const potEl = document.getElementById("rosco-pot-amount");
  const form = document.getElementById("rosco-answer-form");
  const input = document.getElementById("rosco-answer-input");
  const passBtn = document.getElementById("rosco-pass-btn");
  const surrenderBtn = document.getElementById("rosco-surrender-btn");
  const modalRoot = document.getElementById("rosco-modal-root");
  const modalNav = window.GuessDlePlayModalNav?.readFromDataset(gameData) ?? {};

  function postAction(url, body = new URLSearchParams()) {
    return fetch(url, {
      method: "POST",
      headers: {
        "X-CSRFToken": csrf,
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body,
    }).then(async (response) => {
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "Error en la partida.");
      }
      return data;
    });
  }

  function updateWheel(state) {
    Object.entries(state.letters || {}).forEach(([letter, status]) => {
      const node = wheel?.querySelector(`[data-letter="${letter}"]`);
      if (!node) return;
      node.className = `rosco-letter rosco-letter--${status}`;
      const glyph = node.querySelector("span");
      if (glyph) glyph.textContent = letter;
    });
    if (currentLetterEl) {
      currentLetterEl.textContent = state.current_letter || "—";
      currentLetterEl.classList.toggle(
        "rosco-panel__letter-badge--active",
        Boolean(state.current_letter) && state.can_play !== false,
      );
    }
    if (promptEl) promptEl.textContent = state.prompt || "";
    if (potEl && state.pot_amount != null) {
      potEl.textContent = Math.round(Number(state.pot_amount));
    }
  }

  function showModal(title, message, tone = "primary", onClose = null, actionsHtml = null) {
    if (!modalRoot) {
      onClose?.();
      return;
    }

    const actions = actionsHtml ?? `
      <button type="button" class="arcade-btn arcade-btn--${tone} arcade-btn--full" data-close-modal>Aceptar</button>`;
    modalRoot.innerHTML = `
      <div class="arcade-modal-overlay">
        <div class="arcade-modal">
          <button type="button" class="arcade-modal__close" data-close-modal aria-label="Cerrar">&times;</button>
          <h2 class="arcade-modal__title arcade-modal__title--confirm">${title}</h2>
          ${message ? `<p class="arcade-modal__message">${message}</p>` : ""}
          <div class="arcade-modal__actions flex flex-col gap-3 mt-4 w-full max-w-xs">
            ${actions}
          </div>
        </div>
      </div>`;

    const overlay = modalRoot.querySelector(".arcade-modal-overlay");
    window.GuessDleArcadeModal?.mount(overlay);
    const close = () => {
      modalRoot.innerHTML = "";
      onClose?.();
    };

    modalRoot.querySelectorAll("[data-close-modal]").forEach((button) => {
      button.addEventListener("click", close);
    });
    overlay?.addEventListener("click", (event) => {
      if (event.target === overlay) close();
    });
  }

  function showWrongAnswerModal(correctAnswer, onClose) {
    const title = playMessages?.buildModalTitle("wrong_answer", correctAnswer)
      ?? `¡Qué lástima! La respuesta era ${correctAnswer}`;
    showModal(title, "", "secondary", onClose);
  }

  function disablePlayControls() {
    form?.querySelectorAll("input,button").forEach((el) => { el.disabled = true; });
    passBtn?.setAttribute("disabled", "disabled");
    surrenderBtn?.remove();
  }

  function gameEndActionsHtml() {
    return window.GuessDlePlayModalNav?.buildActionsHtml(modalNav)
      ?? `<button type="button" class="arcade-btn arcade-btn--primary arcade-btn--full" data-close-modal>Aceptar</button>`;
  }

  function showGameEndModal(state) {
    if (!state.game_over) return;

    disablePlayControls();
    const actionsHtml = gameEndActionsHtml();
    if (state.won_perfect) {
      showModal(
        "¡Rosco completo!",
        "Has acertado las 27 letras. El bote se repartirá al cierre de la semana entre todos los ganadores perfectos.",
        "primary",
        null,
        actionsHtml,
      );
    } else if (state.session_status === "completed") {
      showModal(
        "Rosco terminado",
        "Has contestado todas las letras. Podrás jugar de nuevo la semana que viene.",
        "secondary",
        null,
        actionsHtml,
      );
    } else if (state.action === "surrender") {
      showModal(
        "Partida rendida",
        "Has abandonado el rosco de esta semana.",
        "secondary",
        null,
        actionsHtml,
      );
    }
  }

  function handleState(state) {
    updateWheel(state);

    if (state.action === "answer" && state.is_correct === false && state.correct_answer) {
      showWrongAnswerModal(state.correct_answer, () => showGameEndModal(state));
      return;
    }

    showGameEndModal(state);
  }

  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!canPlay) return;
    const answer = input?.value.trim();
    if (!answer) return;
    try {
      const body = new URLSearchParams({ answer });
      const state = await postAction(answerUrl, body);
      form.reset();
      handleState(state);
    } catch (error) {
      showModal("Error", error.message, "danger");
    }
  });

  passBtn?.addEventListener("click", async () => {
    if (!canPlay) return;
    try {
      const state = await postAction(passUrl);
      handleState(state);
    } catch (error) {
      showModal("Error", error.message, "danger");
    }
  });

  surrenderBtn?.addEventListener("click", async () => {
    if (!canPlay) return;
    const confirmed = window.confirm("¿Seguro que quieres rendirte? No podrás ganar el bote esta semana.");
    if (!confirmed) return;
    try {
      const state = await postAction(surrenderUrl);
      handleState(state);
    } catch (error) {
      showModal("Error", error.message, "danger");
    }
  });
});
