document.addEventListener('DOMContentLoaded', () => {
  const tabs   = document.querySelectorAll('.pending-tab');
  const panels = document.querySelectorAll('.pending-panel');

  function activate(tabId) {
    panels.forEach(p => p.classList.add('hidden'));
    document.getElementById(`tab-${tabId}`).classList.remove('hidden');

    tabs.forEach(b => {
      b.classList.toggle('bg-yellow-500', b.dataset.tab === tabId);
      b.classList.toggle('text-gray-900', b.dataset.tab === tabId);
      b.classList.toggle('bg-yellow-700', b.dataset.tab !== tabId);
      b.classList.toggle('text-white',     b.dataset.tab !== tabId);
    });
  }

  tabs.forEach(btn =>
    btn.addEventListener('click', () => activate(btn.dataset.tab))
  );

  activate('all');        // pestaña por defecto
});


document.addEventListener('DOMContentLoaded', () => {
  const tabs   = document.querySelectorAll('.active-tab');
  const panels = document.querySelectorAll('.active-panel');

  function activate(tabId) {
    panels.forEach(p => p.classList.add('hidden'));
    document.getElementById(`tab-active-${tabId}`).classList.remove('hidden');

    tabs.forEach(b => {
      const on = b.dataset.tab === tabId;
      b.classList.toggle('bg-yellow-500', on);
      b.classList.toggle('text-gray-900', on);
      b.classList.toggle('bg-yellow-700', !on);
      b.classList.toggle('text-white',   !on);
    });
  }

  tabs.forEach(btn => btn.addEventListener('click', () => activate(btn.dataset.tab)));
  activate('all');   // por defecto
});




