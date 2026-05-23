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




  /* ────── helper: gap según columnas ────── */
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
        .forEach(a => renderAttempt(a, false));   // sin animación
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
          statusMsg.className = "mt-4 font-bold text-center text-lg text-green-700 animate__animated animate__pulse";
        } else {
          statusMsg.textContent = `¡Apuesta perdida! Has perdido ${formatEloAmount(betAmount)} ELO.`;
          statusMsg.className = "mt-4 font-bold text-center text-lg text-red-600 animate__animated animate__shakeX";
        }
      } else if (average !== null && Number(currentAttempts) > average) {
        statusMsg.classList.remove("hidden");
        statusMsg.textContent = `¡Apuesta perdida! Has perdido ${formatEloAmount(betAmount)} ELO.`;
        statusMsg.className = "mt-4 font-bold text-center text-lg text-red-600 animate__animated animate__shakeX";
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

  /* ───────── render intento ───────── */
  function renderAttempt({ name, icon, feedback, guess_image_url }, animate = true) {
    const cols = feedback.length + 1;
    const gap = calcGap(cols);

    const row = document.createElement("div");
    row.className = "attempt-row";
    row.style.display = "grid";
    row.style.gridTemplateColumns = `repeat(${cols}, var(--cell))`;
    row.style.gap = gap;

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
      state: fb, html: `${fb.value}${fb.arrow || ""}`
    })));

    cont.prepend(row);

    /* cabecera la primera vez */
    if (header) {
      header.classList.remove("hidden");             // por si estaba oculta
      header.style.display = "grid";
      header.style.gridTemplateColumns = row.style.gridTemplateColumns;
      header.style.gap = gap;
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
  overlay.style = `
    position:fixed;inset:0;background:rgba(0,0,0,.5);
    display:flex;align-items:center;justify-content:center;z-index:1000;`;

  const modal = document.createElement("div");
  modal.className = `
    bg-amber-100/90 backdrop-blur rounded-3xl p-6 border-4 border-yellow-800
    shadow-lg text-gray-900 w-full max-w-xl animate-bounceInCenter mx-4
    flex flex-col items-center text-center relative`;

  let betMessageHtml = "";
  if (isExtra && betInfo) {
    if (betInfo.betWon) {
      betMessageHtml = `<p class="text-green-700 font-bold mb-4">🎉 ¡Apuesta ganada! Has conseguido +${formatEloAmount(betInfo.netProfit)} ELO.</p>`;
    } else {
      betMessageHtml = `<p class="text-red-600 font-bold mb-4">❌ Apuesta perdida. Has perdido ${formatEloAmount(betInfo.betAmount)} ELO.</p>`;
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
      challengeMessageHtml = `<p class="text-blue-700 font-semibold mb-4">¡Partida completada! Has usado ${attemptsLabel}. Esperando a tu rival...</p>`;
    } else if (normalizedChallenge.winner === normalizedChallenge.current_user) {
      challengeMessageHtml = `<p class="text-green-700 font-bold mb-4">🏆 ¡Has ganado el reto contra ${rivalUsername}! (${userAttempts} vs ${rivalAttempts} intentos)</p>`;
    } else if (normalizedChallenge.winner) {
      challengeMessageHtml = `<p class="text-red-600 font-bold mb-4">💀 Has perdido el reto contra ${rivalUsername}. (${userAttempts} vs ${rivalAttempts} intentos)</p>`;
    } else {
      challengeMessageHtml = `<p class="text-gray-700 font-bold mb-4">🤝 ¡Empate contra ${rivalUsername}! (${userAttempts} vs ${rivalAttempts} intentos)</p>`;
    }
  }

  modal.innerHTML = `
  <button id="close-modal-btn" style="position:absolute;top:10px;right:15px;background:transparent;border:none;font-size:1.5rem;color:black;cursor:pointer;">&times;</button>
  <h2 class="text-2xl font-bold mb-4">
    ¡Correcto! Has adivinado: <span class="text-green-800">${name}</span>
  </h2>
  ${challengeMessageHtml}
  ${betMessageHtml}
  <div class="flex flex-col gap-3 mt-4 w-full max-w-xs">
    <a href="/accounts"
       class="bg-yellow-700 hover:bg-yellow-800 text-white px-6 py-2 rounded-full transition shadow text-center block">
      🏠 Volver al Dashboard
    </a>

    ${!isChallengeModal ? (maxExtrasReached ? `
      <div class="bg-red-100 text-red-800 px-4 py-3 rounded-xl text-center border-2 border-red-300 font-semibold">
        🔒 Ya has jugado tus 2 partidas extra hoy en este juego.
      </div>` : startExtraURL ? `
      <div id="extra-play-wrapper" class="flex flex-col gap-2">
        <button id="show-bet-form"
                class="bg-green-700 hover:bg-green-800 text-white px-6 py-2 rounded-full transition shadow w-full">
          💰 Apostar y jugar partida extra
        </button>
        <form method="post" action="${startExtraURL}" id="bet-form" class="flex flex-col gap-2 hidden">
          <input type="hidden" name="csrfmiddlewaretoken" value="${csrf}">
          <label for="bet" class="text-lg font-semibold text-gray-800">
            ¿Cuánto quieres apostar para jugar una partida extra?
          </label>
          <input type="number" name="bet" min="10" step="1" required
            class="w-full px-4 py-2 border-0 border-green-600 rounded-xl text-center text-lg focus:outline-none focus:ring-green-500 bg-white text-black" style="margin-top: 0.5rem;" />
          <button type="submit"
                  class="bg-green-700 hover:bg-green-700 text-white font-semibold px-6 py-2 rounded-full transition shadow w-full" style="margin-top: 1rem;">
            🎰 ¡Jugar ahora!
          </button>
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
