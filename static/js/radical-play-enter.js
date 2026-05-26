(function () {
  const fromIntro = window.GuessDleBgm?.hasRadicalEnterSignal?.()
    ?? new URLSearchParams(window.location.search).get("radical_enter") === "1";

  if (!fromIntro) {
    document.getElementById("radical-enter-veil")?.remove();
    document.documentElement.classList.remove("radical-enter-pending");
    return;
  }

  const veil = document.getElementById("radical-enter-veil");
  if (!veil) {
    document.documentElement.classList.remove("radical-enter-pending");
    return;
  }

  document.documentElement.classList.add("radical-enter-pending");

  const finishReveal = () => {
    veil.remove();
    document.documentElement.classList.remove("radical-enter-pending");
  };

  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      veil.classList.add("is-revealing");
      veil.addEventListener("transitionend", finishReveal, { once: true });
      window.setTimeout(finishReveal, 1200);
    });
  });
})();
