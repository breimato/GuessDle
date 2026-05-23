/* ranking-tabs.js – cambia entre paneles de ranking */
document.addEventListener('DOMContentLoaded', () => {
  const tabs    = document.querySelectorAll('#ranking-tabs .rank-tab');
  const panels  = document.querySelectorAll('.rank-panel');

  tabs.forEach(btn => {
    btn.addEventListener('click', () => {
      const target = 'tab-' + btn.dataset.tab;

      // botones
      tabs.forEach(b => {
        b.classList.toggle('arcade-tab--active', b === btn);
      });

      // paneles
      panels.forEach(p => p.classList.toggle('hidden', p.id !== target));
    });
  });
});
