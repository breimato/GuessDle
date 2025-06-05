document.addEventListener('DOMContentLoaded', () => {
  const buttons = document.querySelectorAll('.view-btn');
  const panels  = document.querySelectorAll('.view-panel');
  /* ---------- CSRF ---------- */
  const csrftoken = document.querySelector('input[name=csrfmiddlewaretoken]').value;
  const headers   = { 'X-CSRFToken': csrftoken,
                      'Content-Type': 'application/x-www-form-urlencoded' };

  /* ---------- Enviar reto ---------- */
  const form = document.querySelector('#challenge-form');

  buttons.forEach(btn => {
    btn.addEventListener('click', () => {
      /* 1️⃣ Reset botones */
      buttons.forEach(b => {
        b.classList.remove('bg-yellow-500', 'text-gray-900');
        b.classList.add('bg-yellow-700', 'text-white');
      });

      /* 2️⃣ Botón activo */
      btn.classList.remove('bg-yellow-700', 'text-white');
      btn.classList.add('bg-yellow-500', 'text-gray-900');

      /* 3️⃣ Panels */
      const target = 'view-' + btn.dataset.view;
      panels.forEach(p => p.classList.add('hidden'));
      document.getElementById(target)?.classList.remove('hidden');
    });
  });


  
  if (form) {
    form.addEventListener('submit', async (ev) => {
      ev.preventDefault();

      const body = new URLSearchParams(new FormData(form));
      const res  = await fetch(form.action, { method: 'POST', headers, body });
      const data = await res.json();

      if (data.status === 'ok') {
        // nueva tarjeta en “Enviados” sin refrescar
        document.querySelector('#view-enviados')
                .insertAdjacentHTML('afterbegin', data.card);
        form.reset();
      }
    });
  }

  /* ---------- Cancelar o Rechazar ---------- */
  document.body.addEventListener('click', async (ev) => {
    const btn = ev.target.closest('.ajax-delete');
    if (!btn) return;

    ev.preventDefault();

    const res  = await fetch(btn.dataset.url, { method: 'POST', headers });
    const data = await res.json();

    if (data.status === 'ok') {
      // volar la tarjeta del DOM
      btn.closest('.challenge-card')?.remove();
    }
  });
});
