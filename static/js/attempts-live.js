document.addEventListener("DOMContentLoaded", () => {
  /* ───────── nodos básicos ───────── */
  const cont   = document.getElementById("attempts-container");
  const header = document.getElementById("attempts-header");
  const form   = document.getElementById("guess-form");
  const csrf   = document.querySelector("[name=csrfmiddlewaretoken]")?.value;

  /* ───────── 1· historial ───────── */
  const initJSON = document.getElementById("initial-attempts");
  if (initJSON) {
    try {
      JSON.parse(initJSON.textContent)
           .reverse()
           .forEach(a => renderAttempt(a, false));             // sin animación
    } catch (e) { console.error("Historial parse", e); }
  }

  /* ───────── 2· ya ganado previamente ───────── */
  const flag = document.getElementById("won-flag");
  if (flag) {
    disableForm();                       // no más envíos
    setTimeout(() => {                   // leve retraso
      launchConfettiSides();
      showVictoryModal(flag.dataset.champ);
    }, 200);
  }

  /* ───────── 3· envío normal ───────── */
  form?.addEventListener("submit", async e => {
    e.preventDefault();
    const res  = await fetch(form.action, {
      method : "POST",
      headers: { "X-CSRFToken": csrf, "X-Requested-With": "XMLHttpRequest" },
      body   : new FormData(form)
    });
    const data = await res.json();
    if (!res.ok) { alert(data.error || "Error"); return; }

    form.reset();
    const row = renderAttempt(data.attempt, true);

    if (data.won) {
  const cells = row.querySelectorAll(".square");
  const last  = cells[cells.length - 1];           // ← compatible siempre
  if (last) {
    last.addEventListener("animationend", () => {
      disableForm();
      launchConfettiSides();
      showVictoryModal(data.attempt.name);
    }, { once:true });
  } else {
    // por si algo raro: muestra igual tras ½ s
    setTimeout(() => {
      disableForm();
      launchConfettiSides();
      showVictoryModal(data.attempt.name);
    }, 500);
  }
}
  });

  /* ───────── render intento ───────── */
  function renderAttempt({ name, icon, feedback }, animate=true) {
    const row = document.createElement("div");
    row.className = "attempt-row";
    row.style.display = "grid";
    row.style.gridTemplateColumns = `repeat(${feedback.length + 1}, minmax(0,1fr))`;

    row.append(makeCell({
      isStatic:true,
      html:`${icon ? `<img src="${icon}" alt="${name}" style="width:2.2rem;height:2.2rem">` : ""}
           <span class="champion-icon-name">${name}</span>`
    }));
    feedback.forEach(fb => row.append(makeCell({
      state:fb, html:`${fb.value}${fb.arrow || ""}`
    })));

    cont.prepend(row);

    if (header && header.style.display === "none") {
      header.style.display = "grid";
      header.style.gridTemplateColumns = row.style.gridTemplateColumns;
    }

    const cells = row.querySelectorAll(".square");
    if (animate) {
      cells.forEach((c,i)=>setTimeout(()=>{
        c.classList.add("show","animate__animated","animate__flipInY");
        c.style.setProperty("--animate-duration","0.9s");
      }, i*350));
    } else cells.forEach(c=>c.classList.add("show"));
    return row;
  }

  /* ───────── helpers de estado ───────── */
function mapState(fb) {
  if (fb.correct)  return "good";
  if (fb.partial)  return "part";
  if (fb.superior) return "superior";
  return "bad";
}

/* ───────── helpers de celda ───────── */
function makeCell({ isStatic = false, state = null, html = "" }) {
  const d = document.createElement("div");
  d.className = "square" +
                (isStatic ? " square--static" : "") +
                (state ? " square-" + mapState(state) : "");
  d.innerHTML = `<div class="square-content">${html}</div>`;
  return d;
}


  /* ───────── desactiva input/botón ───────── */
  function disableForm(){
    form?.querySelectorAll("input,button").forEach(el=>el.disabled=true);
    form?.classList.add("opacity-50","pointer-events-none");
  }

  /* ───────── modal de victoria ───────── */
  function showVictoryModal(name) {
  injectKeyframes();                           // agrega keyframes si faltan

  /* ── overlay semitransparente ── */
  const overlay = document.createElement("div");
  overlay.style = `
    position:fixed;inset:0;background:rgba(0,0,0,.4);
    display:flex;align-items:center;justify-content:center;
    z-index:1000;`;

  /* ── modal con la misma clase que tu formulario ── */
  const modal = document.createElement("div");
  modal.className = `
  bg-amber-100/90 backdrop-blur rounded-3xl p-6 border-4 border-yellow-800
  shadow-lg text-gray-900 w-full max-w-xl animate-bounceInCenter mx-4
  flex flex-col items-center text-center`;


  modal.innerHTML = `
    <h2 class="text-2xl font-bold mb-4">
      ¡Correcto! Has adivinado:
      <span class="text-green-800">${name}</span>
    </h2>
    <a href="/accounts"
       class="inline-block mt-4 bg-yellow-700 hover:bg-yellow-800 text-white
              px-6 py-2 rounded-full transition shadow">
      Volver al Dashboard
    </a>`;

  overlay.appendChild(modal);
  document.body.appendChild(overlay);
}



  function injectKeyframes(){
    if(document.getElementById("bounce-modal-style")) return;
    const s=document.createElement("style");
    s.id="bounce-modal-style";
    s.textContent=`
    @keyframes bounceInCenter{
      0%{opacity:0;transform:scale(.9) translateY(-40px)}
      60%{opacity:1;transform:scale(1.03) translateY(8px)}
      80%{transform:scale(.97) translateY(-4px)}
      100%{transform:scale(1) translateY(0)}
    }
    .animate-bounceInCenter{animation:bounceInCenter .75s cubic-bezier(.25,.8,.25,1) forwards}`;
    document.head.appendChild(s);
  }

  /* ───────── confetti desde los lados ───────── */
  function launchConfettiSides(){
    const end=Date.now()+2000;
    (function frame(){
      confetti({particleCount:12,angle:60 ,spread:60,origin:{x:0,y:.6}});
      confetti({particleCount:12,angle:120,spread:60,origin:{x:1,y:.6}});
      if(Date.now()<end) requestAnimationFrame(frame);
    })();
  }
});
