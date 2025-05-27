document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("guess-form");
  const cont = document.getElementById("attempts-container");
  const csrf = document.querySelector("[name=csrfmiddlewaretoken]").value;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const data = new FormData(form);

    const res = await fetch(form.action, {
      method: "POST",
      headers: { "X-CSRFToken": csrf, "X-Requested-With": "XMLHttpRequest" },
      body: data
    });

    const json = await res.json();

    if (!res.ok) {
      alert(json.error || "Error");
      return;
    }

    form.reset();
    renderAttempt(json.attempt);

    if (json.won) {
      setTimeout(() => {
        window.location.href = "/dashboard";
      }, 1800);
    }
  });

  function renderAttempt({ name, icon, feedback }) {
    const row = document.createElement("div");
    row.style.gridTemplateColumns = `repeat(${feedback.length + 1}, minmax(0, 1fr))`;

    const champ = document.createElement("div");
    champ.className = "square";
     row.className = "attempt-row";                       //  ←  ¡ESTO Faltaba!

    champ.innerHTML = `
      <div class="square-content">
        ${icon ? `<img src="${icon}" alt="${name}" class="h-12 w-12 object-contain">` : ""}
        <div class="champion-icon-name">${name}</div>
      </div>`;
    row.appendChild(champ);

    feedback.forEach((fb, i) => {
      const cell = document.createElement("div");
      cell.className = `square square-${state(fb)} opacity-0`;
      cell.innerHTML = `
        <div class="square-content">${fb.value}${fb.arrow || ""}</div>`;
      cell.style.animationDelay = `${(i + 1) * 120}ms`;
      row.appendChild(cell);
    });

    cont.prepend(row);
    const cells = row.querySelectorAll(".square");

    /* recorre TODAS (incluye la del campeón) */
    cells.forEach((cell, idx) => {
      setTimeout(() => {
        cell.classList.add("show", "animate__animated", "animate__flipInY");
        cell.style.setProperty("--animate-duration", "0.9s"); // velocidad del giro
      }, idx * 350);   // 350 ms entre columnas → ajústalo a tu gusto
    });

  }

  function state(fb) {
    if (fb.correct) return "good";
    if (fb.partial) return "part";
    return "bad";
  }
});
