(function () {
  const radicalLink = document.querySelector("[data-radical-intro]");
  const bubble = document.getElementById("mode-select-red-bubble");
  const stage = document.querySelector(".mode-select-stage");
  const transition = document.getElementById("mode-select-radical-transition");
  const transitionVeil = transition?.querySelector(".mode-select-radical-transition__veil");

  if (!radicalLink || !bubble || !stage || !transition) {
    return;
  }

  const textElement = bubble.querySelector(".mode-select-gb-bubble__text");
  const dotCount = 8;
  const dotIntervalMs = 170;
  const holdAfterDotsMs = 500;
  const navigateDelayMs = 2000;

  const playUrl = radicalLink.getAttribute("href");
  if (!playUrl || !textElement) {
    return;
  }

  const startTransition = () => {
    bubble.hidden = true;
    bubble.classList.remove("is-visible");
    stage.classList.add("mode-select-stage--departing");

    transition.hidden = false;
    transition.classList.add("is-active");
    requestAnimationFrame(() => {
      transition.classList.add("is-zooming");
      transitionVeil?.classList.add("is-zooming");
    });

    window.setTimeout(() => {
      const targetUrl = new URL(playUrl, window.location.href);
      targetUrl.searchParams.set("radical_enter", "1");
      window.location.assign(targetUrl.toString());
    }, navigateDelayMs);
  };

  radicalLink.addEventListener("click", (event) => {
    event.preventDefault();
    if (stage.classList.contains("mode-select-stage--intro")) {
      return;
    }

    stage.classList.add("mode-select-stage--intro");
    document.body.classList.add("mode-select-body--intro");
    bubble.hidden = false;
    bubble.classList.add("is-visible");
    textElement.textContent = "";
    textElement.classList.remove("is-complete");

    let revealedDots = 0;
    const dotTimer = window.setInterval(() => {
      revealedDots += 1;
      textElement.textContent = ".".repeat(revealedDots);

      if (revealedDots >= dotCount) {
        window.clearInterval(dotTimer);
        textElement.classList.add("is-complete");
        window.setTimeout(startTransition, holdAfterDotsMs);
      }
    }, dotIntervalMs);
  });
})();
