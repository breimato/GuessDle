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

  function buildPollUrl() {
    const url = new URL(pollUrl, window.location.origin);
    if (hasDashboardPanels()) {
      url.searchParams.set("include_dashboard", "1");
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

  function toastMessage(notification) {
    const gameName = notification.payload.game_name || "";
    const rival = notification.payload.opponent_username || "";

    switch (notification.type) {
      case "challenge_received":
        return `${rival} te ha retado en ${gameName}`;
      case "challenge_accepted":
        return `${rival} ha aceptado tu reto en ${gameName}`;
      case "challenge_rejected":
        return `${rival} ha rechazado tu reto en ${gameName}`;
      case "challenge_cancelled":
        return `${rival} ha cancelado el reto en ${gameName}`;
      case "challenge_win":
        return `¡Has ganado el reto de ${gameName} contra ${rival}!`;
      case "challenge_tie":
        return `¡Empate en ${gameName} contra ${rival}!`;
      case "challenge_loss":
        return `¡Has perdido el reto de ${gameName} contra ${rival}!`;
      case "rival_finished":
        return `${rival} ha terminado en ${gameName}. ¡Es tu turno!`;
      default:
        return `Nueva notificación de ${gameName}`;
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

    const text = document.createElement("div");
    text.className = "challenge-toast-text";
    text.textContent = toastMessage(notification);

    const closeBtn = document.createElement("button");
    closeBtn.type = "button";
    closeBtn.className = "challenge-toast-close";
    closeBtn.innerHTML = "&times;";
    closeBtn.addEventListener("click", () => {
      dismissToast(toast);
      ackNotifications([notification.id]);
    });

    content.appendChild(icon);
    content.appendChild(text);
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
