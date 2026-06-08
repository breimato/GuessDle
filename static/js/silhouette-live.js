document.addEventListener("DOMContentLoaded", () => {
  const gameData = document.getElementById("silhouette-game-data");
  if (!gameData) return;

  const BASE_VISIBLE_RATIO = 0.32;
  const RATIO_STEP = 0.08;
  const ALPHA_THRESHOLD = 16;
  const VIEWPORT_FALLBACK_WIDTH = 220;
  const FULL_REVEAL_RATIO = 0.72;

  const playMessages = window.GuessDlePlayMessages;
  const guessUrl = gameData.dataset.guessUrl;
  const surrenderUrl = gameData.dataset.surrenderUrl;
  const canPlay = gameData.dataset.canPlay === "true";
  const modesUrl = gameData.dataset.modesUrl || null;
  const panelUrl = gameData.dataset.panelUrl || "/accounts/";
  const csrf = document.querySelector("[name=csrfmiddlewaretoken]")?.value;
  const viewport = document.getElementById("silhouette-viewport");
  const sprite = document.getElementById("silhouette-sprite");
  const guessesList = document.getElementById("silhouette-guesses-list");
  const form = document.getElementById("silhouette-guess-form");
  const input = document.getElementById("guess");
  const errorEl = document.getElementById("silhouette-guess-error");
  const surrenderBtn = document.getElementById("silhouette-surrender-btn");
  const modalRoot = document.getElementById("silhouette-modal-root");
  const DEFAULT_PORTRAIT = gameData.dataset.defaultPortrait || "/static/images/default-character.png";

  let opaqueBounds = null;

  const isResolvedGame = Boolean(
    document.getElementById("silhouette-won-flag")
    || document.getElementById("silhouette-surrender-flag"),
  );

  if (viewport && sprite && !isResolvedGame) {
    viewport.classList.add("silhouette-viewport--loading");
  }

  function viewportWidth() {
    return viewport?.clientWidth || VIEWPORT_FALLBACK_WIDTH;
  }

  function visibleRatioForLevel(level) {
    return Math.min(1, BASE_VISIBLE_RATIO + level * RATIO_STEP);
  }

  const anchor = gameData.dataset.anchor || "tl";

  function anchorCornerPoint(bounds) {
    if (anchor === "tr") {
      return { x: bounds.maxX, y: bounds.minY };
    }
    if (anchor === "bl") {
      return { x: bounds.minX, y: bounds.maxY };
    }
    if (anchor === "br") {
      return { x: bounds.maxX, y: bounds.maxY };
    }
    return { x: bounds.minX, y: bounds.minY };
  }

  function fullImageBounds(img) {
    const maxX = img.naturalWidth - 1;
    const maxY = img.naturalHeight - 1;
    const bounds = {
      minX: 0,
      minY: 0,
      maxX,
      maxY,
      width: img.naturalWidth,
      height: img.naturalHeight,
    };
    const focus = anchorCornerPoint(bounds);
    return { ...bounds, focusX: focus.x, focusY: focus.y };
  }

  function measureOpaqueBounds(img) {
    const canvas = document.createElement("canvas");
    const context = canvas.getContext("2d");
    if (!context) {
      return null;
    }

    const width = img.naturalWidth;
    const height = img.naturalHeight;
    if (!width || !height) {
      return null;
    }

    canvas.width = width;
    canvas.height = height;
    context.drawImage(img, 0, 0);

    let imageData;
    try {
      imageData = context.getImageData(0, 0, width, height);
    } catch {
      return fullImageBounds(img);
    }

    const data = imageData.data;
    let minX = width;
    let minY = height;
    let maxX = -1;
    let maxY = -1;

    for (let y = 0; y < height; y += 1) {
      for (let x = 0; x < width; x += 1) {
        const alpha = data[(y * width + x) * 4 + 3];
        if (alpha <= ALPHA_THRESHOLD) {
          continue;
        }
        if (x < minX) minX = x;
        if (y < minY) minY = y;
        if (x > maxX) maxX = x;
        if (y > maxY) maxY = y;
      }
    }

    if (maxX < minX || maxY < minY) {
      return fullImageBounds(img);
    }

    const bounds = { minX, minY, maxX, maxY, width, height };
    const corner = anchorCornerPoint(bounds);
    let focusX = corner.x;
    let focusY = corner.y;
    let bestDistanceSq = Number.POSITIVE_INFINITY;

    for (let y = minY; y <= maxY; y += 1) {
      for (let x = minX; x <= maxX; x += 1) {
        const alpha = data[(y * width + x) * 4 + 3];
        if (alpha <= ALPHA_THRESHOLD) {
          continue;
        }
        const deltaX = x - corner.x;
        const deltaY = y - corner.y;
        const distanceSq = deltaX * deltaX + deltaY * deltaY;
        if (distanceSq >= bestDistanceSq) {
          continue;
        }
        bestDistanceSq = distanceSq;
        focusX = x;
        focusY = y;
      }
    }

    return { ...bounds, focusX, focusY };
  }

  function ensureCropIncludesFocus(crop, bounds) {
    const focusX = bounds.focusX;
    const focusY = bounds.focusY;
    if (focusX == null || focusY == null) {
      return crop;
    }

    let cropX = crop.x;
    let cropY = crop.y;

    if (focusX < cropX) {
      cropX = focusX;
    } else if (focusX > cropX + crop.w) {
      cropX = focusX - crop.w;
    }

    if (focusY < cropY) {
      cropY = focusY;
    } else if (focusY > cropY + crop.h) {
      cropY = focusY - crop.h;
    }

    return clampCropToBounds({ x: cropX, y: cropY, w: crop.w, h: crop.h }, bounds);
  }

  function cropRectCentered(bounds, level) {
    const contentW = bounds.maxX - bounds.minX + 1;
    const contentH = bounds.maxY - bounds.minY + 1;
    const ratio = visibleRatioForLevel(level);
    const cropW = contentW * ratio;
    const cropH = contentH * ratio;
    const centerX = (bounds.minX + bounds.maxX) / 2;
    const centerY = (bounds.minY + bounds.maxY) / 2;
    return {
      x: centerX - cropW / 2,
      y: centerY - cropH / 2,
      w: cropW,
      h: cropH,
    };
  }

  function clampCropToBounds(crop, bounds) {
    const contentW = bounds.maxX - bounds.minX + 1;
    const contentH = bounds.maxY - bounds.minY + 1;
    const maxX = bounds.minX + contentW - crop.w;
    const maxY = bounds.minY + contentH - crop.h;

    return {
      x: Math.max(bounds.minX, Math.min(crop.x, maxX)),
      y: Math.max(bounds.minY, Math.min(crop.y, maxY)),
      w: crop.w,
      h: crop.h,
    };
  }

  function computeViewportTransform(bounds, level) {
    const ratio = visibleRatioForLevel(level);
    const contentW = bounds.maxX - bounds.minX + 1;
    const contentH = bounds.maxY - bounds.minY + 1;
    const size = viewportWidth();

    const anchored = cropRectAnchored(bounds, level);
    const centered = cropRectCentered(bounds, level);

    let cropX;
    let cropY;
    let cropW;
    let cropH;

    if (ratio >= 1) {
      cropX = bounds.minX;
      cropY = bounds.minY;
      cropW = contentW;
      cropH = contentH;
    } else {
      cropW = anchored.w;
      cropH = anchored.h;
      if (ratio >= FULL_REVEAL_RATIO) {
        const centerBlend = (ratio - FULL_REVEAL_RATIO) / (1 - FULL_REVEAL_RATIO);
        cropX = anchored.x * (1 - centerBlend) + centered.x * centerBlend;
        cropY = anchored.y * (1 - centerBlend) + centered.y * centerBlend;
      } else {
        cropX = anchored.x;
        cropY = anchored.y;
        if (level === 0) {
          const visibleCrop = ensureCropIncludesFocus(
            { x: cropX, y: cropY, w: cropW, h: cropH },
            bounds,
          );
          cropX = visibleCrop.x;
          cropY = visibleCrop.y;
        }
      }
    }

    const coverScale = size / cropW;
    const coverOffsetX = -cropX * coverScale;
    const coverOffsetY = -cropY * coverScale;

    const containScale = Math.min(size / cropW, size / cropH);
    const containOffsetX = -cropX * containScale + (size - cropW * containScale) / 2;
    const containOffsetY = -cropY * containScale + (size - cropH * containScale) / 2;

    if (ratio <= FULL_REVEAL_RATIO) {
      return {
        scale: coverScale,
        offsetX: coverOffsetX,
        offsetY: coverOffsetY,
      };
    }

    const revealBlend = Math.min(1, (ratio - FULL_REVEAL_RATIO) / (1 - FULL_REVEAL_RATIO));
    return {
      scale: coverScale * (1 - revealBlend) + containScale * revealBlend,
      offsetX: coverOffsetX * (1 - revealBlend) + containOffsetX * revealBlend,
      offsetY: coverOffsetY * (1 - revealBlend) + containOffsetY * revealBlend,
    };
  }

  function cropRectAnchored(bounds, level) {
    const contentW = bounds.maxX - bounds.minX + 1;
    const contentH = bounds.maxY - bounds.minY + 1;
    const ratio = visibleRatioForLevel(level);
    const cropW = contentW * ratio;
    const cropH = contentH * ratio;

    if (anchor === "tr") {
      return {
        x: bounds.maxX - cropW + 1,
        y: bounds.minY,
        w: cropW,
        h: cropH,
      };
    }
    if (anchor === "bl") {
      return {
        x: bounds.minX,
        y: bounds.maxY - cropH + 1,
        w: cropW,
        h: cropH,
      };
    }
    if (anchor === "br") {
      return {
        x: bounds.maxX - cropW + 1,
        y: bounds.maxY - cropH + 1,
        w: cropW,
        h: cropH,
      };
    }
    return {
      x: bounds.minX,
      y: bounds.minY,
      w: cropW,
      h: cropH,
    };
  }

  function clearViewportBackground() {
    if (!viewport) {
      return;
    }

    viewport.style.backgroundImage = "";
    viewport.style.backgroundSize = "";
    viewport.style.backgroundPosition = "";
  }

  function applyContentZoom(bounds, level, options = {}) {
    if (!sprite || !viewport) {
      return;
    }

    const animate = options.animate === true;
    const isFirstPaint = !viewport.style.backgroundImage;

    viewport.classList.remove("silhouette-viewport--revealed");
    viewport.classList.add("silhouette-viewport--playing");

    if (isFirstPaint) {
      viewport.classList.add("silhouette-viewport--loading");
    }

    if (animate) {
      viewport.classList.add("silhouette-viewport--animated");
    }

    const transform = computeViewportTransform(bounds, level);
    const backgroundWidth = bounds.width * transform.scale;
    const backgroundHeight = bounds.height * transform.scale;

    viewport.style.backgroundImage = `url("${sprite.currentSrc || sprite.src}")`;
    viewport.style.backgroundSize = `${backgroundWidth}px ${backgroundHeight}px`;
    viewport.style.backgroundPosition = `${transform.offsetX}px ${transform.offsetY}px`;
    viewport.classList.remove("silhouette-viewport--loading");
  }

  function applyFallbackZoom() {
    if (!sprite || !viewport || !sprite.naturalWidth) {
      clearViewportBackground();
      return;
    }

    applyContentZoom(fullImageBounds(sprite), 0, { animate: false });
  }

  function applyZoom(level, options = {}) {
    if (opaqueBounds) {
      applyContentZoom(opaqueBounds, level, options);
      return;
    }
    applyFallbackZoom();
  }

  function showSpriteLoadError() {
    if (!viewport) {
      return;
    }
    viewport.innerHTML = "<p class=\"silhouette-viewport__error arcade-text-muted\">No se pudo cargar el sprite.</p>";
  }

  function initSpriteZoom() {
    if (!sprite || isResolvedGame) {
      return;
    }

    const onReady = () => {
      opaqueBounds = measureOpaqueBounds(sprite);
      const zoomLevel = Number(gameData.dataset.zoomLevel || 0);
      if (!opaqueBounds) {
        applyFallbackZoom();
        return;
      }
      applyContentZoom(opaqueBounds, zoomLevel, { animate: false });
    };

    if (sprite.complete && sprite.naturalWidth) {
      onReady();
    } else {
      sprite.addEventListener("load", onReady, { once: true });
    }
    sprite.addEventListener("error", showSpriteLoadError, { once: true });
  }

  initSpriteZoom();

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function showModal(title, actionsHtml = "", imageUrl = "") {
    if (!modalRoot) return;
    const imageHtml = imageUrl
      ? `<img src="${escapeHtml(imageUrl)}" alt="" class="silhouette-modal__portrait">`
      : "";
    modalRoot.innerHTML = `
      <div class="arcade-modal-overlay">
        <div class="arcade-modal">
          <button type="button" class="arcade-modal__close" data-close-modal aria-label="Cerrar">&times;</button>
          ${imageHtml}
          <h2 class="arcade-modal__title">${title}</h2>
          <div class="arcade-modal__actions flex flex-col gap-3 mt-4 w-full max-w-xs">
            ${actionsHtml}
          </div>
        </div>
      </div>`;

    const overlay = modalRoot.querySelector(".arcade-modal-overlay");
    window.GuessDleArcadeModal?.mount(overlay);
    const close = () => { modalRoot.innerHTML = ""; };
    modalRoot.querySelectorAll("[data-close-modal]").forEach((button) => {
      button.addEventListener("click", close);
    });
    overlay?.addEventListener("click", (event) => {
      if (event.target === overlay) close();
    });
  }

  function showEndModal(targetName, outcome, imageUrl) {
    const title = playMessages?.buildModalTitle(outcome, targetName)
      ?? (outcome === "surrender"
        ? `¡Qué lástima! El Pokémon era ${targetName}`
        : `¡Correcto! ${targetName}`);
    const navOptions = window.GuessDlePlayModalNav?.readFromDataset(gameData) ?? {
      modesUrl,
      panelUrl,
    };
    const actionsHtml = window.GuessDlePlayModalNav?.buildActionsHtml(navOptions)
      ?? `<a href="${panelUrl}" class="arcade-btn arcade-btn--primary arcade-btn--full">Dashboard</a>`;
    showModal(title, actionsHtml, imageUrl);
    if (outcome === "victory") {
      launchConfettiSides();
    }
  }

  function launchConfettiSides() {
    if (typeof confetti !== "function") return;
    const end = Date.now() + 2000;
    (function frame() {
      confetti({ particleCount: 12, angle: 60, spread: 60, origin: { x: 0, y: 0.6 } });
      confetti({ particleCount: 12, angle: 120, spread: 60, origin: { x: 1, y: 0.6 } });
      if (Date.now() < end) requestAnimationFrame(frame);
    })();
  }

  function disablePlayControls() {
    form?.querySelectorAll("input,button").forEach((el) => { el.disabled = true; });
    form?.classList.add("opacity-50", "pointer-events-none");
    surrenderBtn?.remove();
  }

  function showError(message) {
    if (!errorEl) return;
    errorEl.textContent = message;
    errorEl.classList.remove("hidden");
  }

  function clearError() {
    if (!errorEl) return;
    errorEl.textContent = "";
    errorEl.classList.add("hidden");
  }

  function showFullColorSprite() {
    if (!viewport) {
      return;
    }

    viewport.classList.remove(
      "silhouette-viewport--playing",
      "silhouette-viewport--loading",
      "silhouette-viewport--animated",
    );
    viewport.classList.add("silhouette-viewport--revealed");
    clearViewportBackground();
  }

  function buildGuessCardElement(attempt) {
    const stateClass = attempt.is_correct ? "square-good" : "square-bad";
    const card = document.createElement("div");
    card.className = `silhouette-guess-card square ${stateClass}`;
    const imageUrl = attempt.guess_image_url || DEFAULT_PORTRAIT;
    card.innerHTML = `
      <div class="square-content silhouette-guess-card__content">
        <img
          src="${escapeHtml(imageUrl)}"
          alt="${escapeHtml(attempt.name)}"
          title="${escapeHtml(attempt.name)}"
          class="guess-portrait silhouette-guess-card__portrait"
          onerror="this.onerror=null; this.src='${DEFAULT_PORTRAIT}';">
      </div>`;
    return card;
  }

  function appendGuessCard(attempt) {
    if (!guessesList) return;
    const card = buildGuessCardElement(attempt);
    guessesList.prepend(card);
    requestAnimationFrame(() => {
      card.classList.add("show", "silhouette-guess-card--enter");
    });
  }

  function updateAutocomplete(remainingNames) {
    if (!input || !remainingNames) return;
    input.dataset.names = JSON.stringify(remainingNames);
  }

  function handleState(state) {
    updateAutocomplete(state.remaining_names);

    if (state.won) {
      disablePlayControls();
      showFullColorSprite();
      showEndModal(state.target_name, "victory", state.target_image_url);
      return;
    }

    if (state.surrendered) {
      disablePlayControls();
      showFullColorSprite();
      showEndModal(state.target_name, "surrender", state.target_image_url);
      return;
    }

    applyZoom(state.zoom_level || 0, { animate: true });
  }

  async function postAction(url, body = new URLSearchParams()) {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "X-CSRFToken": csrf,
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body,
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Error en la partida.");
    }
    return data;
  }

  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!canPlay) return;
    clearError();
    const guess = input?.value.trim();
    if (!guess) return;

    try {
      const state = await postAction(guessUrl, new URLSearchParams({ guess }));
      form.reset();
      const lastAttempt = state.attempts?.[state.attempts.length - 1];
      if (lastAttempt) {
        appendGuessCard(lastAttempt);
      }
      handleState(state);
    } catch (error) {
      showError(error.message);
    }
  });

  surrenderBtn?.addEventListener("click", async () => {
    if (!canPlay || !surrenderUrl) return;
    const confirmed = window.confirm("¿Seguro que quieres rendirte? Se revelará la respuesta.");
    if (!confirmed) return;

    try {
      const state = await postAction(surrenderUrl, new URLSearchParams({ csrfmiddlewaretoken: csrf }));
      disablePlayControls();
      showFullColorSprite();
      showEndModal(state.target_name, "surrender", state.target_image_url);
    } catch (error) {
      showError(error.message);
    }
  });

  const wonFlag = document.getElementById("silhouette-won-flag");
  if (wonFlag) {
    disablePlayControls();
    showFullColorSprite();
    setTimeout(
      () => showEndModal(wonFlag.dataset.champ, "victory", wonFlag.dataset.image),
      200,
    );
  }

  const surrenderFlag = document.getElementById("silhouette-surrender-flag");
  if (surrenderFlag) {
    disablePlayControls();
    showFullColorSprite();
    setTimeout(
      () => showEndModal(surrenderFlag.dataset.champ, "surrender", surrenderFlag.dataset.image),
      200,
    );
  }
});
