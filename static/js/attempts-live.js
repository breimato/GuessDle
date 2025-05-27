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

  /* ───────── helpers de celda ───────── */
  function makeCell({isStatic=false,state=null,html=""}) {
    const d=document.createElement("div");
    d.className="square"+(isStatic?" square--static":"")+(state?" square-"+map(state):"");
    d.innerHTML=`<div class="square-content">${html}</div>`;
    return d;
  }
  const map = fb => fb.correct?"good":fb.partial?"part":fb.superior?"superior":"bad";

  /* ───────── desactiva input/botón ───────── */
  function disableForm(){
    form?.querySelectorAll("input,button").forEach(el=>el.disabled=true);
    form?.classList.add("opacity-50","pointer-events-none");
  }

  /* ───────── modal de victoria ───────── */
  function showVictoryModal(name){
    injectKeyframes();

    const overlay=document.createElement("div");
    overlay.style=`
      position:fixed;inset:0;background:rgba(0,0,0,.5);display:flex;
      align-items:center;justify-content:center;z-index:1000;`;

    const modal=document.createElement("div");
    modal.className="animate-bounceInCenter";
    modal.style=`
      background:#fff;border-radius:1rem;padding:2rem 3rem;text-align:center;
      box-shadow:0 8px 20px rgba(0,0,0,.4);max-width:90vw;`;

    modal.innerHTML=`
      <h2 style="font-size:1.6rem;font-weight:700;margin-bottom:1rem;color:#15803d">
        ¡Correcto! Has adivinado: <span>${name}</span>
      </h2>
      <a href="/accounts"
         style="display:inline-block;background:#15803d;color:#fff;padding:.6rem 1.5rem;
                border-radius:9999px;font-weight:600;text-decoration:none">
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
