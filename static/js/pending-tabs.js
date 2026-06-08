document.addEventListener('DOMContentLoaded', () => {
  const showModalMessage = (message, title = 'Aviso') => {
    const overlay = document.createElement('div');
    overlay.className = 'arcade-modal-overlay';
    const modal = document.createElement('div');
    modal.className = 'arcade-modal';
    const titleClass = title === 'Error'
      ? 'arcade-modal__title arcade-modal__title--error'
      : 'arcade-modal__title';
    modal.innerHTML = `
      <button type="button" class="arcade-modal__close" aria-label="Cerrar">&times;</button>
      <h2 class="${titleClass}">${title}</h2>
      <p class="arcade-modal__message">${message}</p>
      <div class="arcade-modal__actions">
        <button type="button" class="arcade-btn arcade-btn--primary arcade-btn--full">Aceptar</button>
      </div>
    `;
    overlay.appendChild(modal);
    document.body.appendChild(overlay);
    window.GuessDleArcadeModal?.mount(overlay);

    const close = () => overlay.remove();
    modal.querySelector('.arcade-modal__close')?.addEventListener('click', close);
    modal.querySelector('.arcade-btn')?.addEventListener('click', close);
    overlay.addEventListener('click', (event) => {
      if (event.target === overlay) {
        close();
      }
    });
  };

  const buildChallengeSuccessMessage = (form) => {
    const opponent = form.querySelector('#opponent')?.selectedOptions[0]?.textContent?.trim();
    const game = form.querySelector('#game')?.selectedOptions[0]?.textContent?.trim();
    const modeSelect = form.querySelector('#challenge-mode');
    const mode = modeSelect && !modeSelect.disabled
      ? modeSelect.selectedOptions[0]?.textContent?.trim()
      : '';

    let message = `Has retado a ${opponent} en ${game}`;
    if (mode) {
      message += ` (${mode})`;
    }
    message += '.';
    return message;
  };

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
      buttons.forEach(b => b.classList.remove('arcade-tab--active'));
      btn.classList.add('arcade-tab--active');

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
        const sentPanel = document.querySelector('#view-sent');
        if (sentPanel) {
          sentPanel.querySelectorAll('.arcade-empty').forEach((node) => node.remove());
          sentPanel.insertAdjacentHTML('afterbegin', data.card);
        }
        showModalMessage(buildChallengeSuccessMessage(form), 'Reto enviado');
        return;
      }

      if (data.message) {
        showModalMessage(data.message, 'Error');
      }
    });
  }

  /* ---------- Cancelar o Rechazar ---------- */
  document.body.addEventListener('click', async (ev) => {
    const acceptBtn = ev.target.closest('.ajax-accept');
    if (acceptBtn) {
      ev.preventDefault();
      const res = await fetch(acceptBtn.dataset.url, { method: 'POST', headers });
      const data = await res.json();
      if (data.status === 'ok' && data.play_url) {
        window.location.href = data.play_url;
        return;
      }
      showModalMessage(
        data.message || 'No puedes aceptar este reto porque todavía no es seguro que tengas esos puntos.',
        'Error'
      );
      return;
    }

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
