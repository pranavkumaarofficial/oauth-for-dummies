/* ============================================================
   Theme switch. Light by default: this is a light system with a
   dark footer, and dark mode is the alternate, not the base.

   Loaded in <head> and applied synchronously so the page never
   paints light first and then flips.
   ============================================================ */

(function () {
  "use strict";

  var KEY = "ofd-theme";

  function resolve() {
    try {
      var saved = localStorage.getItem(KEY);
      if (saved === "light" || saved === "dark") return saved;
    } catch (e) { /* private mode, fall through to the media query */ }

    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  }

  function apply(theme) {
    document.documentElement.setAttribute("data-theme", theme);

    var buttons = document.querySelectorAll("[data-theme-set]");
    for (var i = 0; i < buttons.length; i++) {
      buttons[i].setAttribute("aria-pressed", buttons[i].dataset.themeSet === theme ? "true" : "false");
    }
  }

  // Runs before first paint, so no flash of the wrong theme.
  apply(resolve());

  document.addEventListener("DOMContentLoaded", function () {
    apply(document.documentElement.getAttribute("data-theme"));

    document.addEventListener("click", function (event) {
      var button = event.target.closest && event.target.closest("[data-theme-set]");
      if (!button) return;

      var theme = button.dataset.themeSet;
      apply(theme);
      try { localStorage.setItem(KEY, theme); } catch (e) { /* nothing to do */ }
    });
  });
})();
