/* ranking-tabs.js – cambia entre paneles de ranking */
document.addEventListener('DOMContentLoaded', () => {
  const tabs    = document.querySelectorAll('#ranking-tabs .rank-tab');
  const panels  = document.querySelectorAll('.rank-panel');

  tabs.forEach(btn => {
    btn.addEventListener('click', () => {
      const target = 'tab-' + btn.dataset.tab;

      // botones
      tabs.forEach(b => {
        const active = b === btn;
        b.classList.toggle('bg-yellow-500', active);
        b.classList.toggle('text-gray-900', active);
        b.classList.toggle('bg-yellow-700', !active);
        b.classList.toggle('text-white', !active);
      });

      // paneles
      panels.forEach(p => p.classList.toggle('hidden', p.id !== target));
    });
  });
});
