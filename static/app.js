(function () {
  var root = document.documentElement;
  var toggle = document.getElementById("theme-toggle");

  function label() {
    if (toggle) {
      toggle.textContent = root.getAttribute("data-theme") === "dark" ? "Light" : "Dark";
    }
  }

  var saved = localStorage.getItem("theme");
  if (saved) root.setAttribute("data-theme", saved);
  label();

  if (toggle) {
    toggle.addEventListener("click", function () {
      var next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      localStorage.setItem("theme", next);
      label();
    });
  }

  var np = document.getElementById("next-poll");
  if (np) {
    var interval = parseInt(np.dataset.interval || "300", 10);
    var left = interval;
    function tick() {
      var m = Math.floor(left / 60), s = left % 60;
      np.textContent = (m ? m + "m " : "") + s + "s";
      left = left > 0 ? left - 1 : interval;
    }
    tick();
    setInterval(tick, 1000);
  }
})();
