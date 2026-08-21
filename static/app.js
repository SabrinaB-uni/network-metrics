// NetWatch — theme toggle, live clock, poll countdown. Vanilla JS, no deps.
(function () {
  var root = document.documentElement;

  // --- Theme (persisted) ---------------------------------------------
  var saved = localStorage.getItem("netwatch-theme");
  if (saved) root.setAttribute("data-theme", saved);
  var toggle = document.getElementById("theme-toggle");
  if (toggle) {
    toggle.addEventListener("click", function () {
      var next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      localStorage.setItem("netwatch-theme", next);
    });
  }

  // --- Live clock ----------------------------------------------------
  var clockEl = document.getElementById("clock");
  function tick() {
    if (clockEl) {
      clockEl.textContent = new Date().toLocaleTimeString("en-GB", { hour12: false });
    }
  }
  tick();
  setInterval(tick, 1000);

  // --- Next-poll countdown -------------------------------------------
  var npEl = document.getElementById("next-poll");
  if (npEl) {
    var interval = parseInt(npEl.dataset.interval || "300", 10);
    var remaining = interval;
    function fmt(s) {
      var m = Math.floor(s / 60), ss = s % 60;
      return m ? m + "m " + ss + "s" : ss + "s";
    }
    function count() {
      npEl.textContent = fmt(remaining);
      remaining = remaining > 0 ? remaining - 1 : interval;
    }
    count();
    setInterval(count, 1000);
  }
})();
