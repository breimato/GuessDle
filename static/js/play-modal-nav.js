(function () {
  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function readFromDataset(element) {
    if (!element) {
      return {
        nextModeUrl: "",
        nextModeLabel: "Siguiente modo",
        modesUrl: "",
        panelUrl: "/accounts/",
      };
    }
    return {
      nextModeUrl: element.dataset.nextModeUrl || "",
      nextModeLabel: element.dataset.nextModeLabel || "Siguiente modo",
      modesUrl: element.dataset.modesUrl || "",
      panelUrl: element.dataset.panelUrl || "/accounts/",
    };
  }

  function buildActionsHtml(options = {}) {
    const nextModeUrl = options.nextModeUrl || "";
    const nextModeLabel = options.nextModeLabel || "Siguiente modo";
    const modesUrl = options.modesUrl || "";
    const panelUrl = options.panelUrl || "/accounts/";
    const parts = [];

    if (nextModeUrl) {
      parts.push(
        `<a href="${escapeHtml(nextModeUrl)}" class="arcade-btn arcade-btn--next arcade-btn--full">Siguiente: ${escapeHtml(nextModeLabel)}</a>`
      );
      if (modesUrl) {
        parts.push(
          `<a href="${escapeHtml(modesUrl)}" class="arcade-btn arcade-btn--secondary arcade-btn--full">Modos</a>`
        );
      }
      parts.push(
        `<a href="${escapeHtml(panelUrl)}" class="arcade-btn arcade-btn--primary arcade-btn--full">Dashboard</a>`
      );
      return parts.join("");
    }

    if (modesUrl) {
      parts.push(
        `<a href="${escapeHtml(modesUrl)}" class="arcade-btn arcade-btn--primary arcade-btn--full">Modos</a>`
      );
    }
    parts.push(
      `<a href="${escapeHtml(panelUrl)}" class="arcade-btn ${modesUrl ? "arcade-btn--secondary" : "arcade-btn--primary"} arcade-btn--full">Dashboard</a>`
    );
    return parts.join("");
  }

  window.GuessDlePlayModalNav = {
    readFromDataset,
    buildActionsHtml,
  };
})();
