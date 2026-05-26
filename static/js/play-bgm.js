document.addEventListener("DOMContentLoaded", () => {
  const slider = document.getElementById("play-bgm-volume-slider")
    || document.getElementById("challenge-volume-slider");
  const upButton = document.getElementById("play-bgm-volume-up")
    || document.getElementById("challenge-volume-up");
  const downButton = document.getElementById("play-bgm-volume-down")
    || document.getElementById("challenge-volume-down");

  if (!slider || !window.GuessDleBgm) {
    return;
  }

  window.GuessDleBgm.bindVolumeControls(slider, upButton, downButton);
});
