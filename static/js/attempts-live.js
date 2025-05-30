document.addEventListener("DOMContentLoaded", () => {
  /* ───────── nodos básicos ───────── */
  const cont = document.getElementById("attempts-container");
  const header = document.getElementById("attempts-header");
  const form = document.getElementById("guess-form");
  const csrf = document.querySelector("[name=csrfmiddlewaretoken]")?.value;
  const slugMatch = location.pathname.match(/\/play(?:-extra)?\/([^\/]+)/);
  const slug = slugMatch ? slugMatch[1] : null;
  const startExtraURL = slug ? `/games/start-extra/${slug}/` : null;


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

  /* ───────── 2· ya ganado previamente ───────── */
  const flag = document.getElementById("won-flag");
  if (flag) {
    disableForm();
    setTimeout(() => {
      launchConfettiSides();
      showVictoryModal(flag.dataset.champ);
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


    if (data.won) {
      const cells = row.querySelectorAll(".square");
      const last = cells[cells.length - 1];
      if (last) {
        last.addEventListener("animationend", () => {
          disableForm();
          launchConfettiSides();
          showVictoryModal(data.attempt.name);
        }, { once: true });
      } else {
        setTimeout(() => {
          disableForm();
          launchConfettiSides();
          showVictoryModal(data.attempt.name);
        }, 500);
      }

      if (IS_CHALLENGE === "true") {
        const attemptsPlayed = document.querySelectorAll("#attempts-container > *").length;

        fetch(CHALLENGE_REPORT_URL, {
          method: "POST",
          headers: {
            "X-CSRFToken": CSRF_TOKEN,
            "Content-Type": "application/x-www-form-urlencoded",
          },
          body: new URLSearchParams({ attempts: attemptsPlayed }),
        }).catch(err => console.error("Error al reportar intento:", err));
      }
    }
  });

  /* ───────── render intento ───────── */
  function renderAttempt({ name, icon, feedback }, animate = true) {
    const cols = feedback.length + 1;
    const gap = calcGap(cols);

    const row = document.createElement("div");
    row.className = "attempt-row";
    /* ⬇️ cambio clave: usamos var(--cell) para ancho fijo, no 1fr */
    row.style.cssText = `display:grid;grid-template-columns:repeat(${cols},var(--cell));gap:${gap}`;

    row.append(makeCell({
      isStatic: true,
      html: `${icon ? `<img src="${icon}" alt="${name}" style="width:2.2rem;height:2.2rem">` : ""}
           <span class="champion-icon-name">${name}</span>`
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

  /* ───────── modal victoria ───────── */
  function showVictoryModal(name) {
  injectKeyframes();

  const overlay = document.createElement("div");
  overlay.style = `
    position:fixed;inset:0;background:rgba(0,0,0,.5);
    display:flex;align-items:center;justify-content:center;z-index:1000;`;

  const modal = document.createElement("div");
  modal.className = `
    bg-amber-100/90 backdrop-blur rounded-3xl p-6 border-4 border-yellow-800
    shadow-lg text-gray-900 w-full max-w-xl animate-bounceInCenter mx-4
    flex flex-col items-center text-center`;

  modal.innerHTML = `
    <h2 class="text-2xl font-bold mb-4">
      ¡Correcto! Has adivinado: <span class="text-green-800">${name}</span>
    </h2>
    <div class="flex flex-col gap-3 mt-4 w-full max-w-xs">
      <a href="/accounts"
         class="bg-yellow-700 hover:bg-yellow-800 text-white px-6 py-2 rounded-full transition shadow text-center block">
        🏠 Volver al Dashboard
      </a>
      ${startExtraURL ? `
        <div id="extra-play-wrapper" class="flex flex-col gap-2">
          <button id="show-bet-form"
                  class="bg-green-700 hover:bg-green-800 text-white px-6 py-2 rounded-full transition shadow w-full">
            💰 Apostar y jugar partida extra
          </button>
          <form method="post" action="${startExtraURL}" id="bet-form" class="flex flex-col gap-2 hidden">
            <input type="hidden" name="csrfmiddlewaretoken" value="${csrf}">
            <label for="bet" class="text-lg font-semibold text-gray-800">
              ¿Cuánto quieres apostar para jugar una partida extra?
            <input type="number" name="bet" min="10" step="1" required
              class="w-full px-4 py-2 border-0 border-green-600 rounded-xl text-center text-lg focus:outline-none focus:ring-green-500 bg-white text-black" style="margin-top: 0.5rem;" />
            <button type="submit"
                    class="bg-green-700 hover:bg-green-700 text-white font-semibold px-6 py-2 rounded-full transition shadow w-full" style="margin-top: 1rem;">
              🎰 ¡Jugar ahora!
            </button>
          </form>
        </div>` : ''}
    </div>
  `;

  overlay.appendChild(modal);
  document.body.appendChild(overlay);

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

  function reportChallengeResult(attempts) {
    const input = document.getElementById("challenge-attempts-input");
    input.value = attempts;
    document.getElementById("challenge-report-form").submit();
  }

  // Hook automático si ganaste
  const wonFlag = document.getElementById("won-flag");
  if (wonFlag) {
    // Contar los intentos jugados
    const attempts = document.querySelectorAll("#attempts-container > *").length;
    reportChallengeResult(attempts);
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
