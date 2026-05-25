const CHALLENGE_VOLUME_KEY = "guessdle-challenge-volume";
const DEFAULT_VOLUME = 0.3;
const STEP = 0.05;

document.addEventListener("DOMContentLoaded", () => {
  const audio = document.getElementById("challenge-bgm");
  const slider = document.getElementById("challenge-volume-slider");
  const upBtn = document.getElementById("challenge-volume-up");
  const downBtn = document.getElementById("challenge-volume-down");
  if (!audio || !slider) return;

  const stored = localStorage.getItem(CHALLENGE_VOLUME_KEY);
  const percent = stored !== null ? Number(stored) : Math.round(DEFAULT_VOLUME * 100);

  const applyVolume = (value) => {
    const clamped = Math.min(1, Math.max(0, value));
    audio.volume = clamped;
    const pct = Math.round(clamped * 100);
    slider.value = String(pct);
    slider.setAttribute("aria-valuenow", slider.value);
    localStorage.setItem(CHALLENGE_VOLUME_KEY, slider.value);
  };

  applyVolume(percent / 100);

  slider.addEventListener("input", () => {
    applyVolume(Number(slider.value) / 100);
  });

  upBtn?.addEventListener("click", () => {
    applyVolume(audio.volume + STEP);
  });

  downBtn?.addEventListener("click", () => {
    applyVolume(audio.volume - STEP);
  });

  const startPlayback = () => {
    audio.play().catch(() => {});
  };

  startPlayback();
  document.addEventListener(
    "click",
    () => {
      if (audio.paused) startPlayback();
    },
    { once: true }
  );
});
