/* ============================================================
   Learn Mode stepper.

   Drives three things from one piece of state — the current step:
     1. which panel is shown
     2. which tab is marked active/past
     3. which hop and actors light up in the flow diagram

   No framework, no build step. Everything is already in the DOM;
   this only toggles classes. If JavaScript is off, every panel is
   visible and the page still reads top to bottom.
   ============================================================ */

(function () {
  "use strict";

  var root = document.querySelector("[data-stepper]");
  if (!root) return;

  var panels = Array.prototype.slice.call(root.querySelectorAll("[data-step]"));
  var tabs = Array.prototype.slice.call(document.querySelectorAll("[data-step-tab]"));
  var hops = Array.prototype.slice.call(document.querySelectorAll("[data-hop]"));
  var actors = Array.prototype.slice.call(document.querySelectorAll("[data-actor]"));

  var prevBtn = document.querySelector("[data-step-prev]");
  var nextBtn = document.querySelector("[data-step-next]");
  var counter = document.querySelector("[data-step-count]");

  if (!panels.length) return;

  var total = panels.length;
  var current = 1;

  // Which actors are involved in each hop, so the columns light up too.
  var HOP_ACTORS = {
    1: ["browser", "provider"],
    2: ["provider", "app"],
    3: ["app", "provider"],
    4: ["app", "provider"],
    5: ["app", "browser"]
  };

  function clamp(n) {
    return Math.min(Math.max(n, 1), total);
  }

  function render() {
    panels.forEach(function (panel) {
      panel.classList.toggle("is-active", Number(panel.dataset.step) === current);
    });

    tabs.forEach(function (tab) {
      var n = Number(tab.dataset.stepTab);
      tab.classList.toggle("is-active", n === current);
      tab.classList.toggle("is-past", n < current);
      tab.setAttribute("aria-selected", n === current ? "true" : "false");
    });

    hops.forEach(function (hop) {
      var n = Number(hop.dataset.hop);
      hop.classList.toggle("is-active", n === current);
      hop.classList.toggle("is-past", n < current);
    });

    var lit = HOP_ACTORS[current] || [];
    actors.forEach(function (actor) {
      actor.classList.toggle("is-active", lit.indexOf(actor.dataset.actor) !== -1);
    });

    if (prevBtn) prevBtn.disabled = current === 1;
    if (nextBtn) nextBtn.disabled = current === total;
    if (counter) counter.textContent = current + " / " + total;

    // Keep the URL shareable — someone can link straight to step 3.
    if (window.history && window.history.replaceState) {
      window.history.replaceState(null, "", "#step-" + current);
    }
  }

  function go(n) {
    var next = clamp(n);
    if (next === current) return;
    current = next;
    render();
  }

  tabs.forEach(function (tab) {
    tab.addEventListener("click", function () {
      go(Number(tab.dataset.stepTab));
    });
  });

  // Anything else that jumps to a step — the Replay button, for instance.
  document.querySelectorAll("[data-step-goto]").forEach(function (el) {
    el.addEventListener("click", function () {
      go(Number(el.dataset.stepGoto));
      el.blur();
    });
  });

  if (prevBtn) prevBtn.addEventListener("click", function () { go(current - 1); });
  if (nextBtn) nextBtn.addEventListener("click", function () { go(current + 1); });

  document.addEventListener("keydown", function (event) {
    if (event.metaKey || event.ctrlKey || event.altKey) return;
    var tag = (event.target.tagName || "").toLowerCase();
    if (tag === "input" || tag === "textarea") return;

    if (event.key === "ArrowRight") { go(current + 1); event.preventDefault(); }
    else if (event.key === "ArrowLeft") { go(current - 1); event.preventDefault(); }
    else if (/^[1-9]$/.test(event.key)) { go(Number(event.key)); event.preventDefault(); }
  });

  // Deep link support: /learn/github/result#step-3
  var fromHash = /^#step-(\d+)$/.exec(window.location.hash);
  if (fromHash) current = clamp(Number(fromHash[1]));

  // Only now take over the layout, so no-JS keeps every panel visible.
  root.classList.add("is-enhanced");
  render();
})();
