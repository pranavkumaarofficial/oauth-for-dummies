/* ============================================================
   Copy buttons on the Settings page.

   Callback URLs get mistyped constantly, and a redirect_uri that is
   off by one character is the most common way an OAuth setup fails.
   Copying beats retyping.
   ============================================================ */

(function () {
  "use strict";

  function flash(button, message) {
    var original = button.dataset.originalLabel || button.textContent;
    button.dataset.originalLabel = original;
    button.textContent = message;
    setTimeout(function () { button.textContent = original; }, 1400);
  }

  function fallbackCopy(text) {
    // Clipboard API needs a secure context. localhost counts, but a plain
    // http host on the LAN does not, so keep the old path around.
    var field = document.createElement("textarea");
    field.value = text;
    field.setAttribute("readonly", "");
    field.style.position = "fixed";
    field.style.opacity = "0";
    document.body.appendChild(field);
    field.select();

    var ok = false;
    try { ok = document.execCommand("copy"); } catch (e) { ok = false; }
    document.body.removeChild(field);
    return ok;
  }

  document.addEventListener("click", function (event) {
    var button = event.target.closest && event.target.closest("[data-copy]");
    if (!button) return;

    var text = button.dataset.copy;

    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(
        function () { flash(button, "Copied"); },
        function () { flash(button, fallbackCopy(text) ? "Copied" : "Press Ctrl+C"); }
      );
    } else {
      flash(button, fallbackCopy(text) ? "Copied" : "Press Ctrl+C");
    }
  });
})();
