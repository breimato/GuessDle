const PLAY_VOLUME_KEY = "guessdle-play-volume";
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

function clearRadicalEnterUrlParam() {
  const url = new URL(window.location.href);
  if (!url.searchParams.has(RADICAL_ENTER_PARAM)) {
    return;
  }
  url.searchParams.delete(RADICAL_ENTER_PARAM);
  const nextPath = `${url.pathname}${url.search}${url.hash}`;
  history.replaceState(null, "", nextPath || url.pathname);
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

function waitForSourceReady(audio) {
  if (audio.readyState >= 1) {
    return Promise.resolve();
  }
  return new Promise((resolve) => {
    audio.addEventListener("loadedmetadata", resolve, { once: true });
  });
}

async function configureSource(audio, src, loop) {
  audio.loop = loop;
  if (sourcesMatch(audio, src)) {
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
    return true;
  } catch (_error) {
    const resumeOnGesture = () => {
      audio.currentTime = resumeTime;
      audio.play().catch(() => {});
    };
    document.addEventListener("click", resumeOnGesture, { once: true });
    document.addEventListener("keydown", resumeOnGesture, { once: true });
    return false;
  }
}

const GuessDleBgm = {
  getAudio: getGlobalBgmAudio,
  readStoredVolumePercent,

  async start({ src, loop = true, restart = true }) {
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

  async ensurePagePlayback(pageConfig) {
    if (!pageConfig?.src) {
      return;
    }

    await GuessDleBgm.start({
      src: pageConfig.src,
      loop: pageConfig.loop !== false,
      restart: true,
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

document.addEventListener("DOMContentLoaded", async () => {
  const audio = getGlobalBgmAudio();
  const pageConfig = window.GuessDleBgmPage;

  if (pageConfig) {
    await GuessDleBgm.ensurePagePlayback(pageConfig);
    clearRadicalEnterUrlParam();
    return;
  }

  if (audio && !audio.paused) {
    audio.pause();
  }
});
