document.addEventListener("DOMContentLoaded", () => {
  const muteToggle = document.getElementById("lol-launcher-mute");
  const audio = window.GuessDleBgm?.getAudio?.();

  if (!muteToggle || !audio) {
    return;
  }

  muteToggle.addEventListener("change", () => {
    audio.muted = muteToggle.checked;
  });
});
