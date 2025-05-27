document.addEventListener("DOMContentLoaded", () => {
  /* ---------- nodos clave ---------- */
  const form   = document.getElementById("guess-form");
  const cont   = document.getElementById("attempts-container");
  const header = document.getElementById("attempts-header");
  const csrf   = document.querySelector("[name=csrfmiddlewaretoken]").value;

  /* ---------- 1) pintar historial SIN animación ---------- */
  const initTag = document.getElementById("initial-attempts");
  if (initTag) {
    try {
      JSON.parse(initTag.textContent)
           .reverse()                     // cronológico ascendente
           .forEach(attempt => renderAttempt(attempt, false));  // 👈 sin animar
    } catch (err) {
      console.error("No se pudo parsear initial-attempts", err);
    }
  }

  /* ---------- 2) interceptar submit (animación SÍ) ---------- */
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
    renderAttempt(data.attempt, true);    // 👈 animar nuevo intento

    if (data.won) setTimeout(() => location.href = "/dashboard", 1800);
  });

  /* ---------- 3) dibuja UNA fila ---------- */
  /** @param animate {boolean} true = flip escalonado, false = estático **/
  function renderAttempt({ name, icon, feedback }, animate = true) {
    const cols = feedback.length + 1;

    /* contenedor grid */
    const row = document.createElement("div");
    row.className = "attempt-row";
    row.style.gridTemplateColumns = `repeat(${cols}, minmax(0,1fr))`;

    /* celda campeón */
    row.append(makeCell({
      isStatic: true,
      html: `${icon ? `<img src="${icon}" alt="${name}" style="width:2.2rem;height:2.2rem">` : ""}
             <span class="champion-icon-name">${name}</span>`
    }));

    /* celdas feedback */
    feedback.forEach(fb => row.append(makeCell({
      state: fb,
      html : `${fb.value}${fb.arrow || ""}`
    })));

    /* inserta arriba */
    cont.prepend(row);

    /* mostrar / sincronizar cabecera */
    if (header && header.style.display === "none") {
      header.style.display = "grid";
      header.style.gridTemplateColumns = row.style.gridTemplateColumns;
    }

    /* animar solo si es un intento nuevo */
    if (animate) {
      row.querySelectorAll(".square").forEach((cell, idx) => {
        setTimeout(() => {
          cell.classList.add("show","animate__animated","animate__flipInY");
          cell.style.setProperty("--animate-duration","0.9s");
        }, idx * 350);
      });
    } else {
      /* historial: se muestran todos de golpe */
      row.querySelectorAll(".square").forEach(cell => cell.classList.add("show"));
    }
  }

  /* ---------- helpers ---------- */
  function makeCell({ isStatic=false, state=null, html="" } = {}) {
    const div = document.createElement("div");
    div.className = "square" +
                    (isStatic ? " square--static" : "") +
                    (state    ? " square-" + mapState(state) : "");
    div.innerHTML = `<div class="square-content">${html}</div>`;
    return div;
  }
  function mapState(fb){
    if (fb.correct)  return "good";
    if (fb.partial)  return "part";
    if (fb.superior) return "superior";
    return "bad";
  }
});
