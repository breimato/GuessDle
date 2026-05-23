document.addEventListener("DOMContentLoaded", () => {
  /* ───────── nodos básicos ───────── */
  const cont = document.getElementById("attempts-container");
  const header = document.getElementById("attempts-header");
  const form = document.getElementById("guess-form");
  const csrf = document.querySelector("[name=csrfmiddlewaretoken]")?.value;
  const slugMatch = location.pathname.match(/\/play(?:-extra)?\/([^\/]+)/);
  const gameData = document.getElementById("game-data");
  const slug = gameData?.dataset.slug;
  const extraId = gameData?.dataset.extraId;
  const startExtraURL = slug ? `/games/start-extra/${slug}/` : null;
  const maxExtrasReached = document.getElementById("game-data")?.dataset.maxExtrasReached === "true";




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

  function formatEloAmount(amount) {
    const n = Number(amount);
    if (Number.isNaN(n)) return "0";
    return Number.isInteger(n) ? n : n.toFixed(1);
  }

  function getBetAverage() {
    const avg = betData?.global_average;
    if (avg == null || avg === "") return null;
    const n = Number(avg);
    return Number.isNaN(n) ? null : n;
  }

  function getBetAmount() {
    return Number(betData?.bet_amount ?? 0);
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

  function updateBetTrackerUI(currentAttempts, won = false, betInfo = null) {
    if (!betData) return;

    const statusMsg = document.getElementById("bet-status-msg");
    const average = getBetAverage();
    const betAmount = betInfo?.betAmount ?? getBetAmount();

    if (statusMsg) {
      if (won) {
        statusMsg.classList.remove("hidden");
        if (betInfo?.betWon) {
          statusMsg.textContent = `¡Apuesta ganada! +${formatEloAmount(betInfo.netProfit)} ELO`;
          statusMsg.className = "mt-2 font-bold text-center text-lg arcade-msg--bet-win";
        } else {
          statusMsg.textContent = `¡Apuesta perdida! Has perdido ${formatEloAmount(betAmount)} ELO.`;
          statusMsg.className = "mt-2 font-bold text-center text-lg arcade-msg--bet-loss";
        }
      } else if (average !== null && Number(currentAttempts) > average) {
        statusMsg.classList.remove("hidden");
        statusMsg.textContent = `¡Apuesta perdida! Has perdido ${formatEloAmount(betAmount)} ELO.`;
        statusMsg.className = "mt-2 font-bold text-center text-lg arcade-msg--bet-loss";
      } else {
        statusMsg.classList.add("hidden");
      }
    }
  }

  if (betData) {
    const currentCount = document.querySelectorAll("#attempts-container > *").length;
    const wonFlagEl = document.getElementById("won-flag");
    const initialWon = wonFlagEl !== null;
    const initialBetInfo = wonFlagEl && wonFlagEl.dataset.isExtra === "true"
      ? {
          betAmount: parseFloat(wonFlagEl.dataset.betAmount || "0"),
          betWon: wonFlagEl.dataset.betWon === "true",
          netProfit: parseFloat(wonFlagEl.dataset.netProfit || "0"),
        }
      : null;
    updateBetTrackerUI(currentCount, initialWon, initialBetInfo);
  }

  function normalizeChallengeData(data) {
    if (!data) return null;
    const currentUser = data.current_user
      ?? (typeof CHALLENGE_CURRENT_USER !== "undefined" ? CHALLENGE_CURRENT_USER : "");
    return {
      completed: Boolean(data.completed),
      current_user: currentUser,
      challenger: data.challenger ?? data.challenger_username ?? "",
      opponent: data.opponent ?? data.opponent_username ?? "",
      winner: data.winner ?? data.winner_username ?? null,
      challenger_attempts: data.challenger_attempts,
      opponent_attempts: data.opponent_attempts,
    };
  }

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

  /* ───────── 2· ya ganado previamente ───────── */
  const flag = document.getElementById("won-flag");
  if (flag) {
    disableForm();
    setTimeout(async () => {
      launchConfettiSides();
      const isExtra = flag.dataset.isExtra === "true";
      const betInfo = isExtra
        ? {
            betAmount: parseFloat(flag.dataset.betAmount || "0"),
            betWon: flag.dataset.betWon === "true",
            netProfit: parseFloat(flag.dataset.netProfit || "0"),
          }
        : null;
      const isChallengeReload = typeof IS_CHALLENGE !== "undefined" && IS_CHALLENGE === "true";
      let challengeData = null;
      if (isChallengeReload) {
        const attemptsPlayed = document.querySelectorAll("#attempts-container > *").length;
        try {
          challengeData = await fetchChallengeReport(attemptsPlayed);
        } catch (err) {
          console.error("Challenge report failed:", err);
        }
      }
      handleGameCompletion(flag.dataset.champ, isExtra, betInfo, challengeData);
    }, 200);
  }

  /* ───────── 3· envío normal ───────── */
  form?.addEventListener("submit", async e => {
    e.preventDefault();
    const res = await fetch(form.action, {
      method: "POST",
      headers: { "X-CSRFToken": csrf, "X-Requested-With": "XMLHttpRequest" },
      body: new FormData(form)
    });

    const data = await res.json();
    if (!res.ok) { alert(data.error || "Error"); return; }

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
      const currentCount = document.querySelectorAll("#attempts-container > *").length;
      updateBetTrackerUI(currentCount, data.won, betInfo);
    }

    if (data.won) {
      const cells = row.querySelectorAll(".square");
      const last = cells[cells.length - 1];
      const runCompletion = async () => {
        disableForm();
        launchConfettiSides();
        const isChallenge = typeof IS_CHALLENGE !== "undefined" && IS_CHALLENGE === "true";
        let challengeData = null;
        if (isChallenge) {
          const attemptsPlayed = document.querySelectorAll("#attempts-container > *").length;
          try {
            challengeData = await fetchChallengeReport(attemptsPlayed);
          } catch (err) {
            console.error("Challenge report failed:", err);
          }
        }
        handleGameCompletion(data.attempt.name, !!extraId, betInfo, challengeData);
      };
      if (last) {
        last.addEventListener("animationend", runCompletion, { once: true });
      } else {
        setTimeout(runCompletion, 500);
      }
    }
  });

  function capitalize(text) {
    return text.replace(/\b\w/g, char => char.toUpperCase());
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

    // Lógica para la celda del personaje/ítem
    let characterCellHtml = "";
    if (guess_image_url) {
      characterCellHtml = `
        <img
          src="${guess_image_url}"
          alt="${capitalize(name)}"
          title="${capitalize(name)}"
          style="width: 100px; height: 100px; object-fit: cover; object-position: top;"
          onerror="this.onerror=null; this.src='/static/images/default-character.png';"
        >
      `;
    } else { // Fallback al nombre si no hay ni imagen ni icono
      characterCellHtml = `<span class="champion-icon-name">${name}</span>`;
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


  /**
   * Decide which completion overlay or modal to show.
   */

  function handleGameCompletion(targetName, isExtra, betInfo = null, challengeData = null) {
    showVictoryModal(targetName, isExtra, betInfo, challengeData);
  }

  /* ───────── modal victoria ───────── */
  function showVictoryModal(name, isExtra = false, betInfo = null, challengeData = null) {
  injectKeyframes();

  const overlay = document.createElement("div");
  overlay.className = "arcade-modal-overlay";

  const modal = document.createElement("div");
  modal.className = "arcade-modal animate-bounceInCenter";

  let betMessageHtml = "";
  if (isExtra && betInfo) {
    if (betInfo.betWon) {
      betMessageHtml = `<p class="arcade-msg--bet-win">¡Apuesta ganada! +${formatEloAmount(betInfo.netProfit)} ELO</p>`;
    } else {
      betMessageHtml = `<p class="arcade-msg--bet-loss">Apuesta perdida. Has perdido ${formatEloAmount(betInfo.betAmount)} ELO.</p>`;
    }
  }

  const isChallengeModal = typeof IS_CHALLENGE !== "undefined" && IS_CHALLENGE === "true";

  let challengeMessageHtml = "";
  const normalizedChallenge = normalizeChallengeData(challengeData);
  if (normalizedChallenge) {
    const isChallenger = normalizedChallenge.current_user === normalizedChallenge.challenger;
    const rivalUsername = isChallenger ? normalizedChallenge.opponent : normalizedChallenge.challenger;
    const userAttempts = isChallenger
      ? normalizedChallenge.challenger_attempts
      : normalizedChallenge.opponent_attempts;
    const rivalAttempts = isChallenger
      ? normalizedChallenge.opponent_attempts
      : normalizedChallenge.challenger_attempts;
    const attemptsLabel = userAttempts != null ? `${userAttempts} intentos` : "tus intentos";

    if (!normalizedChallenge.completed) {
      challengeMessageHtml = `<p class="arcade-msg--wait">Partida completada (${attemptsLabel}). Esperando a tu rival…</p>`;
    } else if (normalizedChallenge.winner === normalizedChallenge.current_user) {
      challengeMessageHtml = `<p class="arcade-msg--win">¡Has ganado el reto contra ${rivalUsername}! (${userAttempts} vs ${rivalAttempts})</p>`;
    } else if (normalizedChallenge.winner) {
      challengeMessageHtml = `<p class="arcade-msg--loss">Has perdido el reto contra ${rivalUsername}. (${userAttempts} vs ${rivalAttempts})</p>`;
    } else {
      challengeMessageHtml = `<p class="arcade-msg--tie">Empate contra ${rivalUsername}. (${userAttempts} vs ${rivalAttempts})</p>`;
    }
  }

  modal.innerHTML = `
  <button id="close-modal-btn" class="arcade-modal__close">&times;</button>
  <h2 class="arcade-modal__title">¡Correcto! ${name}</h2>
  ${challengeMessageHtml}
  ${betMessageHtml}
  <div class="flex flex-col gap-3 mt-4 w-full max-w-xs">
    <a href="/accounts" class="arcade-btn arcade-btn--primary arcade-btn--full">Volver al Dashboard</a>

    ${!isChallengeModal ? (maxExtrasReached ? `
      <div class="arcade-alert arcade-alert--error text-center">Ya has jugado tus 2 partidas extra hoy.</div>` : startExtraURL ? `
      <div id="extra-play-wrapper" class="flex flex-col gap-2 w-full">
        <button id="show-bet-form" class="arcade-btn arcade-btn--secondary arcade-btn--full">Apostar y jugar extra</button>
        <form method="post" action="${startExtraURL}" id="bet-form" class="flex flex-col gap-2 hidden">
          <input type="hidden" name="csrfmiddlewaretoken" value="${csrf}">
          <label for="bet" class="arcade-label">¿Cuánto quieres apostar?</label>
          <input type="number" name="bet" min="10" step="1" required class="arcade-input" />
          <button type="submit" class="arcade-btn arcade-btn--primary arcade-btn--full">¡Jugar ahora!</button>
        </form>
      </div>` : '') : ''}
  </div>`;


  overlay.appendChild(modal);
  document.body.appendChild(overlay);


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
  }
}


  function injectKeyframes() {
    if (document.getElementById("bounce-modal-style")) return;
    const s = document.createElement("style");
    s.id = "bounce-modal-style";
    s.textContent = `
      @keyframes bounceInCenter{
        0%{opacity:0;transform:scale(.9) translateY(-40px)}
        60%{opacity:1;transform:scale(1.03) translateY(8px)}
        80%{transform:scale(.97) translateY(-4px)}
        100%{transform:scale(1) translateY(0)}
      }
      .animate-bounceInCenter{
        animation:bounceInCenter .75s cubic-bezier(.25,.8,.25,1) forwards;
      }`;
    document.head.appendChild(s);
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

  const showBetFormBtn = document.getElementById("show-bet-form");
  const betForm = document.getElementById("bet-form");

  if (showBetFormBtn && betForm) {
    showBetFormBtn.addEventListener("click", () => {
      showBetFormBtn.style.display = "none";
      betForm.classList.remove("hidden");
    });
  }

});
