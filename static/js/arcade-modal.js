(function () {
  function replayEnterAnimation(overlay) {
    if (!overlay) return;
    overlay.classList.remove("is-opening");
    void overlay.offsetWidth;
    overlay.classList.add("is-opening");
  }

  function mount(overlay) {
    replayEnterAnimation(overlay);
    return overlay;
  }

  function open(overlay) {
    if (!overlay) return;
    overlay.hidden = false;
    replayEnterAnimation(overlay);
  }

  function close(overlay) {
    if (!overlay) return;
    overlay.hidden = true;
    overlay.classList.remove("is-opening");
  }

  window.GuessDleArcadeModal = {
    mount,
    open,
    close,
    replayEnterAnimation,
  };
})();
