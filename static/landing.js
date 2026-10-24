// Landing page: select a soil band to reveal the crops that suit it.
document.querySelectorAll(".strata .stratum").forEach((band, _i, all) => {
  band.addEventListener("click", () => {
    all.forEach((b) => {
      const on = b === band;
      b.classList.toggle("is-active", on);
      b.setAttribute("aria-pressed", String(on));
    });
  });
});
