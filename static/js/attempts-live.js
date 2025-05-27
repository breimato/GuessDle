document.addEventListener("DOMContentLoaded", () => {
  /* ---------- nodos ---------- */
  const form   = document.getElementById("guess-form");
  const cont   = document.getElementById("attempts-container");
  const header = document.getElementById("attempts-header");
  const csrf   = document.querySelector("[name=csrfmiddlewaretoken]").value;

  /* ---------- 1· historial ---------- */
  const init = document.getElementById("initial-attempts");
  if (init) {
    try {
      JSON.parse(init.textContent)
           .reverse()
           .forEach(a => renderAttempt(a, false));
    } catch (e) { console.error("historial parse", e); }
  }

  /* ---------- 2· submit ---------- */
  form.addEventListener("submit", async e => {
    e.preventDefault();

    const res  = await fetch(form.action, {
      method : "POST",
      headers: { "X-CSRFToken": csrf, "X-Requested-With": "XMLHttpRequest" },
      body   : new FormData(form)
    });
    const data = await res.json();
    if (!res.ok) { alert(data.error || "Error"); return; }

    form.reset();
    const rowEl = renderAttempt(data.attempt, true);

    if (data.won) onRowFinished(rowEl, celebrate);
  });

  /* ---------- render fila ---------- */
  function renderAttempt({ name, icon, feedback }, animate = true) {
    const cols = feedback.length + 1;
    const row  = document.createElement("div");
    row.className = "attempt-row";
    row.style.gridTemplateColumns = `repeat(${cols}, minmax(0,1fr))`;

    row.append(makeCell({
      isStatic:true,
      html:`${icon ? `<img src="${icon}" alt="${name}" style="width:2.2rem;height:2.2rem">` : ""}
           <span class="champion-icon-name">${name}</span>`
    }));

    feedback.forEach(fb => row.append(makeCell({
      state:fb,
      html :`${fb.value}${fb.arrow || ""}`
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
      },i*350));
    } else cells.forEach(c=>c.classList.add("show"));

    return row;
  }

  /* espera al final del flip */
  function onRowFinished(row, cb){
    const cells = row.querySelectorAll(".square");
    if (!cells.length) { cb(); return; }
    const last = cells[cells.length-1];
    last.addEventListener("animationend", cb, { once:true });
  }

  /* ---------- CELEBRACIÓN ---------- */
  function celebrate(){
    launchConfettiSides();
    showSlideModal();
  }

  /* confeti lados */
  function launchConfettiSides(){
    const end = Date.now() + 3000;
    (function frame(){
      confetti({particleCount:12,angle:60, spread:55, origin:{x:0, y:0.7}});
      confetti({particleCount:12,angle:120,spread:55, origin:{x:1, y:0.7}});
      if(Date.now() < end) requestAnimationFrame(frame);
    })();
  }

  /* modal con slide-down */
  function showSlideModal() {
  // inyecta keyframes si aún no existen
  if (!document.getElementById("bounce-modal-style")) {
    const style = document.createElement("style");
    style.id = "bounce-modal-style";
    style.textContent = `
    @keyframes bounceInCenter {
      0%   { opacity: 0; transform: scale(0.9) translateY(-30px); }
      60%  { opacity: 1; transform: scale(1.02) translateY(10px); }
      80%  { transform: scale(0.98) translateY(-4px); }
      100% { transform: scale(1) translateY(0); }
    }`;
    document.head.appendChild(style);
  }

  // overlay oscuro
  const overlay = document.createElement("div");
  overlay.style = `
    position:fixed;inset:0;display:flex;align-items:center;justify-content:center;
    background:rgba(0,0,0,.4);z-index:1000;`;

  // modal centrado con rebote
  const modal = document.createElement("div");
  modal.style = `
    background:#fff;border-radius:1rem;padding:2rem 3rem;text-align:center;
    animation: bounceInCenter 0.7s ease forwards;`;

  modal.innerHTML = `
    <h2 style="font-size:1.6rem;font-weight:700;margin-bottom:1rem;color:#15803d">
      ¡Correcto!
    </h2>
    <a href="/accounts/"
       style="display:inline-block;background:#15803d;color:#fff;padding:.6rem 1.5rem;
              border-radius:9999px;font-weight:600;text-decoration:none">
      Volver al Dashboard
    </a>`;

  overlay.appendChild(modal);
  document.body.appendChild(overlay);
}



  /* ---------- helpers ---------- */
  function makeCell({isStatic=false,state=null,html=""}={}){
    const d=document.createElement("div");
    d.className="square"+(isStatic?" square--static":"")+(state?" square-"+map(state):"");
    d.innerHTML=`<div class="square-content">${html}</div>`;
    return d;
  }
  function map(fb){
    if(fb.correct) return"good";
    if(fb.partial) return"part";
    if(fb.superior)return"superior";
    return"bad";
  }
});
