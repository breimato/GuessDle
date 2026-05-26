const PLAY_VOLUME_KEY = "guessdle-play-volume";
const BGM_STATE_KEY = "guessdle-bgm-state";
const BGM_HANDOFF_KEY = "guessdle-bgm-handoff";
const BGM_FADE_IN_KEY = "guessdle-radical-fade-in";
const RADICAL_ENTER_PARAM = "radical_enter";
const DEFAULT_VOLUME = 0.3;

function getGlobalBgmAudio() {
  return document.getElementById("global-bgm");
}

function readStoredVolumePercent() {
  const stored = localStorage.getItem(PLAY_VOLUME_KEY);
  if (stored !== null) {
    return Number(stored);
  }
  const legacyStored = localStorage.getItem("guessdle-challenge-volume");
  if (legacyStored !== null) {
    return Number(legacyStored);
  }
  return Math.round(DEFAULT_VOLUME * 100);
}

function applyVolumeToAudio(audio, percent) {
  audio.volume = Math.min(1, Math.max(0, percent / 100));
}

function readPersistedState() {
  const raw = sessionStorage.getItem(BGM_STATE_KEY);
  if (!raw) {
    return null;
  }
  try {
    return JSON.parse(raw);
  } catch (_error) {
    return null;
  }
}

function writePersistedState() {
  const audio = getGlobalBgmAudio();
  if (!audio || !audio.src) {
    return;
  }

  sessionStorage.setItem(
    BGM_STATE_KEY,
    JSON.stringify({
      src: audio.currentSrc || audio.src,
      time: audio.currentTime,
      playing: !audio.paused,
      loop: audio.loop,
    })
  );
}

function clearPersistedState() {
  sessionStorage.removeItem(BGM_STATE_KEY);
}

function hasRadicalEnterSignal() {
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get(RADICAL_ENTER_PARAM) === "1") {
    return true;
  }
  return (
    sessionStorage.getItem(BGM_HANDOFF_KEY) === "1"
    || sessionStorage.getItem(BGM_FADE_IN_KEY) === "1"
  );
}

function clearRadicalEnterUrlParam() {
  const url = new URL(window.location.href);
  if (!url.searchParams.has(RADICAL_ENTER_PARAM)) {
    return;
  }
  url.searchParams.delete(RADICAL_ENTER_PARAM);
  const nextPath = `${url.pathname}${url.search}${url.hash}`;
  history.replaceState(null, "", nextPath || url.pathname);
}

function markHandoff() {
  writePersistedState();
  sessionStorage.setItem(BGM_HANDOFF_KEY, "1");
  sessionStorage.setItem(BGM_FADE_IN_KEY, "1");
}

function consumeRadicalEnter() {
  const hadEnter = hasRadicalEnterSignal();
  sessionStorage.removeItem(BGM_HANDOFF_KEY);
  sessionStorage.removeItem(BGM_FADE_IN_KEY);
  clearRadicalEnterUrlParam();
  return hadEnter;
}

function normalizeSourcePath(src) {
  try {
    return new URL(src, window.location.origin).pathname;
  } catch (_error) {
    return src;
  }
}

function sourcesMatch(audio, targetSrc) {
  if (!audio?.src || !targetSrc) {
    return false;
  }
  return normalizeSourcePath(audio.src) === normalizeSourcePath(targetSrc);
}

function resolvePlaybackSource(pageSrc, persistedSrc) {
  if (persistedSrc) {
    return persistedSrc;
  }
  return pageSrc;
}

function waitForSourceReady(audio) {
  if (audio.readyState >= 1) {
    return Promise.resolve();
  }
  return new Promise((resolve) => {
    audio.addEventListener("loadedmetadata", resolve, { once: true });
  });
}

async function configureSource(audio, src, loop) {
  const needsNewSource = !sourcesMatch(audio, src);
  audio.loop = loop;
  if (!needsNewSource) {
    return;
  }

  audio.src = src;
  await waitForSourceReady(audio);
}

async function seekAndPlay(audio, targetTime) {
  const resumeTime = Math.max(0, targetTime);
  audio.currentTime = resumeTime;

  try {
    await audio.play();
    writePersistedState();
    return true;
  } catch (_error) {
    const resumeOnGesture = () => {
      audio.currentTime = resumeTime;
      audio.play().then(writePersistedState).catch(() => {});
    };
    document.addEventListener("click", resumeOnGesture, { once: true });
    document.addEventListener("keydown", resumeOnGesture, { once: true });
    return false;
  }
}

const GuessDleBgm = {
  getAudio: getGlobalBgmAudio,
  readStoredVolumePercent,
  persist: writePersistedState,
  clearPersisted: clearPersistedState,
  markHandoff,
  hasRadicalEnterSignal,
  consumeRadicalEnter,

  async start({ src, loop = true, restart = false }) {
    const audio = getGlobalBgmAudio();
    if (!audio || !src) {
      return;
    }

    await configureSource(audio, src, loop);
    applyVolumeToAudio(audio, readStoredVolumePercent());

    if (restart) {
      audio.currentTime = 0;
    }

    await seekAndPlay(audio, audio.currentTime);
  },

  async restoreHandoff(pageConfig) {
    const audio = getGlobalBgmAudio();
    if (!audio || !pageConfig?.src) {
      return false;
    }

    const persisted = readPersistedState();
    const playbackSrc = resolvePlaybackSource(pageConfig.src, persisted?.src);
    const loop = pageConfig.loop !== false;
    const resumeTime = persisted?.time ?? 0;

    await configureSource(audio, playbackSrc, loop);
    applyVolumeToAudio(audio, readStoredVolumePercent());
    return seekAndPlay(audio, resumeTime);
  },

  async ensurePagePlayback(pageConfig) {
    if (!pageConfig?.src) {
      return;
    }

    await GuessDleBgm.start({
      src: pageConfig.src,
      loop: pageConfig.loop !== false,
      restart: pageConfig.resume !== true,
    });
  },

  bindVolumeControls(slider, upButton, downButton) {
    const audio = getGlobalBgmAudio();
    if (!audio || !slider) {
      return null;
    }

    const applyVolume = (value) => {
      const clamped = Math.min(1, Math.max(0, value));
      audio.volume = clamped;
      const percent = Math.round(clamped * 100);
      slider.value = String(percent);
      slider.setAttribute("aria-valuenow", slider.value);
      localStorage.setItem(PLAY_VOLUME_KEY, slider.value);
    };

    applyVolume(readStoredVolumePercent() / 100);

    slider.addEventListener("input", () => {
      applyVolume(Number(slider.value) / 100);
    });

    upButton?.addEventListener("click", () => {
      applyVolume(audio.volume + 0.05);
    });

    downButton?.addEventListener("click", () => {
      applyVolume(audio.volume - 0.05);
    });

    return applyVolume;
  },
};

window.GuessDleBgm = GuessDleBgm;
window.GuessDlePlayBgm = {
  PLAY_VOLUME_KEY,
  readStoredVolumePercent,
  bindPlayBgmControls: GuessDleBgm.bindVolumeControls,
};

function persistOnHide() {
  writePersistedState();
}

window.addEventListener("pagehide", persistOnHide);
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "hidden") {
    persistOnHide();
  }
});

document.addEventListener("DOMContentLoaded", () => {
  const audio = getGlobalBgmAudio();
  const pageConfig = window.GuessDleBgmPage;
  const isRadicalEnter = consumeRadicalEnter();

  if (pageConfig) {
    if (pageConfig.resume && isRadicalEnter) {
      GuessDleBgm.restoreHandoff(pageConfig);
      return;
    }

    GuessDleBgm.ensurePagePlayback(pageConfig);
    return;
  }

  if (audio && !audio.paused) {
    audio.pause();
  }
  clearPersistedState();
});
