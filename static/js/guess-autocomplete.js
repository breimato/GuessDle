/* guess-autocomplete.js — lee nombres desde data-names */
document.addEventListener('DOMContentLoaded', () => {
  const input = document.getElementById('guess');
  if (!input) return;

  let names = [];
  try {
    names = JSON.parse(input.dataset.names || '[]');
  } catch (err) {
    console.error('autocomplete: JSON inválido en data-names', err);
  }

  const box = document.getElementById('suggestions');
  let hl = -1;

  const clearActive = () => [...box.children].forEach(i => i.classList.remove('suggestion-active'));
  const close       = () => { box.classList.add('hidden'); input.setAttribute('aria-expanded', 'false'); hl = -1; };
  const setVal      = v => { input.value = v; close(); input.focus(); };

  const paint = q => {
    box.innerHTML = ''; hl = -1;
    let fresh = [];
    try { fresh = JSON.parse(input.dataset.names || '[]'); } catch {}
    const res = q ? fresh.filter(n => n.toLowerCase().includes(q)).slice(0, 15) : [];

    if (!res.length) { close(); return; }

    res.forEach((n, i) => {
      const li = Object.assign(document.createElement('li'), {
        textContent: n,
        role: 'option',
        className: 'suggestion px-4 py-2 cursor-pointer transition'
      });
      li.onmouseenter = () => { clearActive(); li.classList.add('suggestion-active'); hl = i; };
      li.onclick      = () => setVal(n);
      box.appendChild(li);
    });
    box.classList.remove('hidden');
    input.setAttribute('aria-expanded', 'true');
  };

  const move = d => {
    const items = [...box.children];
    if (!items.length) return;
    clearActive();
    hl = (hl + d + items.length) % items.length;
    items[hl].classList.add('suggestion-active');
    items[hl].scrollIntoView({ block: 'nearest' });
  };

  input.addEventListener('input', () => paint(input.value.toLowerCase()));
  input.addEventListener('keydown', e => {
    if (box.classList.contains('hidden')) return;
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault(); move(1); break;
      case 'ArrowUp':
        e.preventDefault(); move(-1); break;
      case 'Tab':
        e.preventDefault();
        if (hl === -1) hl = 0;
        setVal(box.children[hl]?.textContent || '');
        break;
      case 'Enter':
        if (hl > -1) {
          e.preventDefault();
          setVal(box.children[hl].textContent);
        } else if (box.children.length) {
          e.preventDefault();
          setVal(box.children[0].textContent);
        }
        break;
      case 'Escape':
        close(); break;
    }
  });


  document.addEventListener('click', e => {
    if (!box.contains(e.target) && e.target !== input) close();
  });
});
