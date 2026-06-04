(function () {
  const yearMin = document.getElementById("year_min");
  const yearMax = document.getElementById("year_max");
  const eraTiles = document.querySelectorAll(".proximity-filter-tile--lol-era");
  if (!yearMin || !yearMax || !eraTiles.length) {
    return;
  }

  function syncEraHighlight() {
    const min = Number(yearMin.value);
    const max = Number(yearMax.value);
    eraTiles.forEach((tile) => {
      const tileMin = Number(tile.dataset.yearMin);
      const tileMax = Number(tile.dataset.yearMax);
      const active = min === tileMin && max === tileMax;
      tile.classList.toggle("is-active", active);
      tile.setAttribute("aria-pressed", active ? "true" : "false");
    });
  }

  eraTiles.forEach((tile) => {
    tile.addEventListener("click", () => {
      yearMin.value = tile.dataset.yearMin;
      yearMax.value = tile.dataset.yearMax;
      syncEraHighlight();
    });
  });

  yearMin.addEventListener("input", syncEraHighlight);
  yearMax.addEventListener("input", syncEraHighlight);
  syncEraHighlight();
})();
