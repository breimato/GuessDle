(function () {
  const pollUrlMeta = document.querySelector('meta[name="notifications-poll-url"]');
  const ackUrlMeta = document.querySelector('meta[name="notifications-ack-url"]');
  const csrfInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
  const csrfMeta = document.querySelector('meta[name="csrf-token"]');

  if (!pollUrlMeta || !ackUrlMeta) {
    return;
  }

  const pollUrl = pollUrlMeta.content;
  const ackUrl = ackUrlMeta.content;
  const csrfToken = csrfInput
    ? csrfInput.value
    : (csrfMeta ? csrfMeta.content : getCookie("csrftoken"));
  const shownNotificationIds = new Set();
  const pollIntervalMs = 5000;
  const toastLifetimeMs = 10000;
  const dashboardPanels = {
    pending: "view-pending",
    active: "view-active",
    sent: "view-sent",
  };

  function getCookie(name) {
    const match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
    return match ? decodeURIComponent(match[2]) : "";
  }

  function hasDashboardPanels() {
    return Boolean(document.getElementById(dashboardPanels.active));
  }

  function hasDashboardStats() {
    return Boolean(document.getElementById("user-stats-body"));
  }

  function hasRankingPanels() {
    return Boolean(document.querySelector("[data-ranking-tab]"));
  }

  function buildPollUrl() {
    const url = new URL(pollUrl, window.location.origin);
    if (hasDashboardPanels()) {
      url.searchParams.set("include_dashboard", "1");
    }
    if (hasDashboardStats()) {
      url.searchParams.set("include_stats", "1");
    }
    if (hasRankingPanels()) {
      url.searchParams.set("include_rankings", "1");
    }
    return url.toString();
  }

  function getToastContainer() {
    let container = document.getElementById("challenge-toast-container");
    if (!container) {
      container = document.createElement("div");
      container.id = "challenge-toast-container";
      document.body.appendChild(container);
    }
    return container;
  }

  function toastClassForType(type) {
    if (type === "challenge_win") return "toast-win";
    if (type === "challenge_tie") return "toast-tie";
    return "toast-loss";
  }

  function toastIconForType(type) {
    if (type === "challenge_win") return "🏆";
    if (type === "challenge_tie") return "🤝";
    if (type === "challenge_received") return "⚔️";
    if (type === "challenge_accepted") return "✅";
    if (type === "rival_finished") return "⏳";
    return "💀";
  }

  function buildDeltaLabel(notification) {
    const pointsDelta = Number(notification.payload.points_delta);
    const hasDelta = !Number.isNaN(pointsDelta) && pointsDelta !== 0;
    if (!hasDelta) {
      return "";
    }
    return pointsDelta > 0 ? `+${pointsDelta} ELO` : `${pointsDelta} ELO`;
  }

  function toastMessage(notification) {
    const gameName = notification.payload.game_name || "";
    const rival = notification.payload.opponent_username || "";

    switch (notification.type) {
      case "challenge_received":
        return { mainText: `${rival} te ha retado en ${gameName}`, deltaText: "" };
      case "challenge_accepted":
        return { mainText: `${rival} ha aceptado tu reto en ${gameName}`, deltaText: "" };
      case "challenge_rejected":
        return { mainText: `${rival} ha rechazado tu reto en ${gameName}`, deltaText: "" };
      case "challenge_cancelled":
        return { mainText: `${rival} ha cancelado el reto en ${gameName}`, deltaText: "" };
      case "challenge_win":
        return {
          mainText: `¡Has ganado el reto de ${gameName} contra ${rival}!`,
          deltaText: buildDeltaLabel(notification),
        };
      case "challenge_tie":
        return {
          mainText: `¡Empate en ${gameName} contra ${rival}!`,
          deltaText: buildDeltaLabel(notification),
        };
      case "challenge_loss":
        return {
          mainText: `¡Has perdido el reto de ${gameName} contra ${rival}!`,
          deltaText: buildDeltaLabel(notification),
        };
      case "rival_finished":
        return { mainText: `${rival} ha terminado en ${gameName}. ¡Es tu turno!`, deltaText: "" };
      default:
        return { mainText: `Nueva notificación de ${gameName}`, deltaText: "" };
    }
  }

  function dismissToast(toast) {
    toast.classList.add("toast-hide");
    toast.addEventListener("animationend", () => toast.remove(), { once: true });
  }

  function showToast(notification) {
    const container = getToastContainer();
    const toast = document.createElement("div");
    toast.className = `challenge-toast ${toastClassForType(notification.type)}`;
    toast.dataset.notificationId = String(notification.id);

    const content = document.createElement("div");
    content.className = "challenge-toast-content";

    const icon = document.createElement("span");
    icon.className = "challenge-toast-icon";
    icon.textContent = toastIconForType(notification.type);

    const textWrap = document.createElement("div");
    textWrap.className = "challenge-toast-text";
    const message = toastMessage(notification);
    const mainLine = document.createElement("div");
    mainLine.textContent = message.mainText;
    textWrap.appendChild(mainLine);
    if (message.deltaText) {
      const deltaLine = document.createElement("div");
      deltaLine.className = "challenge-toast-delta";
      deltaLine.textContent = message.deltaText;
      textWrap.appendChild(deltaLine);
    }

    const closeBtn = document.createElement("button");
    closeBtn.type = "button";
    closeBtn.className = "challenge-toast-close";
    closeBtn.innerHTML = "&times;";
    closeBtn.addEventListener("click", () => {
      dismissToast(toast);
      ackNotifications([notification.id]);
    });

    content.appendChild(icon);
    content.appendChild(textWrap);
    toast.appendChild(content);
    toast.appendChild(closeBtn);
    container.appendChild(toast);

    setTimeout(() => {
      if (toast.isConnected) {
        dismissToast(toast);
      }
    }, toastLifetimeMs);
  }

  async function ackNotifications(notificationIds) {
    if (!notificationIds.length) {
      return;
    }

    const body = new URLSearchParams({ ids: notificationIds.join(",") });
    await fetch(ackUrl, {
      method: "POST",
      headers: {
        "X-CSRFToken": csrfToken,
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body,
    });
  }

  function removeEmptyState(panelElement) {
    panelElement.querySelectorAll(".arcade-empty").forEach((node) => node.remove());
  }

  function removeChallengeCards(challengeId) {
    document.querySelectorAll(`[data-challenge-id="${challengeId}"]`).forEach((node) => {
      node.remove();
    });
  }

  function insertChallengeCard(panelKey, challengeId, html) {
    const panelId = dashboardPanels[panelKey];
    const panel = document.getElementById(panelId);
    if (!panel) {
      return;
    }

    removeEmptyState(panel);
    if (panel.querySelector(`[data-challenge-id="${challengeId}"]`)) {
      return;
    }

    panel.insertAdjacentHTML("afterbegin", html);
  }

  function updateChallengeCard(panelKey, challengeId, html) {
    const panelId = dashboardPanels[panelKey];
    const panel = document.getElementById(panelId);
    if (!panel) {
      return;
    }

    const existingCard = panel.querySelector(`[data-challenge-id="${challengeId}"]`);
    if (existingCard) {
      existingCard.outerHTML = html;
      return;
    }

    insertChallengeCard(panelKey, challengeId, html);
  }

  function applyDashboardSync(dashboardSync) {
    if (!dashboardSync) {
      return;
    }

    (dashboardSync.removes || []).forEach(removeChallengeCards);

    (dashboardSync.inserts || []).forEach((insert) => {
      insertChallengeCard(insert.panel, insert.challenge_id, insert.html);
    });

    (dashboardSync.updates || []).forEach((update) => {
      updateChallengeCard(update.panel, update.challenge_id, update.html);
    });
  }

  function formatPoints(value) {
    const numericValue = Number(value || 0);
    return String(Math.round(numericValue));
  }

  function formatAverage(value) {
    const numericValue = Number(value || 0);
    return numericValue.toFixed(2);
  }

  function renderUserStatsRows(rows) {
    if (!rows || !rows.length) {
      return `
        <tr>
          <td colspan="3" class="arcade-empty">Sin datos</td>
        </tr>
      `;
    }
    return rows.map((row) => `
      <tr>
        <td>${row.name}</td>
        <td>${formatAverage(row.average_attempts)}</td>
        <td><strong>${formatPoints(row.points)}</strong></td>
      </tr>
    `).join("");
  }

  function applyStatsSync(statsSync) {
    if (!statsSync) {
      return;
    }
    const badge = document.getElementById("global-elo-badge");
    if (badge && statsSync.global_elo != null) {
      badge.textContent = `${formatPoints(statsSync.global_elo)} ELO`;
    }
    const tableBody = document.getElementById("user-stats-body");
    if (tableBody) {
      tableBody.innerHTML = renderUserStatsRows(statsSync.games || []);
    }
  }

  function renderRankingRows(rows) {
    if (!rows || !rows.length) {
      return `
        <tr>
          <td colspan="5" class="arcade-empty">Sin datos</td>
        </tr>
      `;
    }
    return rows.map((row, index) => {
      const position = index + 1;
      const rankVariant = position === 1 ? "1" : (position === 2 ? "2" : (position === 3 ? "3" : "n"));
      const rankLabel = position === 1 ? "🥇" : (position === 2 ? "🥈" : (position === 3 ? "🥉" : String(position)));
      const averageLabel = row.average_attempts == null ? "–" : formatAverage(row.average_attempts);
      return `
        <tr>
          <td>
            <div class="arcade-rank-badge arcade-rank-badge--${rankVariant}">
              ${rankLabel}
            </div>
          </td>
          <td>${row.username}</td>
          <td><strong>${formatPoints(row.points)}</strong></td>
          <td>${averageLabel}</td>
          <td>${row.games_finished}</td>
        </tr>
      `;
    }).join("");
  }

  function renderRankingTable(rows) {
    return `
      <table class="arcade-table">
        <thead>
          <tr>
            ${rows && rows.length ? "<th></th>" : ""}
            <th>Jugador</th>
            <th>Puntos</th>
            <th>Media</th>
            <th>Partidas</th>
          </tr>
        </thead>
        <tbody>
          ${renderRankingRows(rows)}
        </tbody>
      </table>
    `;
  }

  function applyRankingSync(rankingSync) {
    if (!rankingSync) {
      return;
    }
    const globalPanel = document.querySelector('[data-ranking-tab="global"]');
    if (globalPanel) {
      globalPanel.innerHTML = renderRankingTable(rankingSync.global_ranking || []);
    }

    const rankingByGame = rankingSync.ranking_by_game || {};
    Object.entries(rankingByGame).forEach(([gameSlug, gameRanking]) => {
      if (gameRanking && !Array.isArray(gameRanking) && typeof gameRanking === "object") {
        Object.entries(gameRanking).forEach(([modeSlug, modeRows]) => {
          const panel = document.querySelector(`[data-ranking-tab="${gameSlug}-${modeSlug}"]`);
          if (panel) {
            panel.innerHTML = renderRankingTable(modeRows || []);
          }
        });
        return;
      }
      const panel = document.querySelector(`[data-ranking-tab="${gameSlug}"]`);
      if (panel) {
        panel.innerHTML = renderRankingTable(gameRanking || []);
      }
    });
  }

  async function pollNotifications() {
    if (document.hidden) {
      return;
    }

    try {
      const response = await fetch(buildPollUrl(), {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      if (!response.ok) {
        return;
      }

      const data = await response.json();
      if (data.status !== "ok") {
        return;
      }

      applyDashboardSync(data.dashboard_sync);
      applyStatsSync(data.stats_sync);
      applyRankingSync(data.ranking_sync);

      const freshNotifications = (data.notifications || []).filter(
        (notification) => !shownNotificationIds.has(notification.id)
      );

      if (!freshNotifications.length) {
        return;
      }

      freshNotifications.forEach((notification) => {
        shownNotificationIds.add(notification.id);
        showToast(notification);
      });

      await ackNotifications(freshNotifications.map((notification) => notification.id));
    } catch (_error) {
      return;
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    pollNotifications();
    setInterval(pollNotifications, pollIntervalMs);
  });
})();
