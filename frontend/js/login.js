(function () {
  var $ = function (id) { return document.getElementById(id); };
  var params = new URLSearchParams(window.location.search);

  // Si ya hay sesión abierta en esta pestaña, va directo al panel
  if (window.SESSION.get() && !params.get("error")) { location.replace("panel.html"); return; }

  if (params.get("course_id") && /^\d+$/.test(params.get("course_id"))) $("cid").value = params.get("course_id");
  if (params.get("error")) $("err").textContent = params.get("error");

  $("loginForm").addEventListener("submit", async function (e) {
    e.preventDefault();
    var v = $("uid").value.trim(), c = $("cid").value.trim();
    if (!/^\d+$/.test(v) || !/^\d+$/.test(c)) { $("err").textContent = "Ingresa IDs numéricos válidos para estudiante y curso."; return; }
    $("err").textContent = ""; $("loginBtn").disabled = true;
    try {
      await API.login(v, c);
      window.SESSION.set(v, c);
      location.href = "panel.html";
    } catch (er) {
      $("err").textContent = /fetch|network/i.test(er.message) ? "No se pudo conectar con el servidor." : er.message;
      $("loginBtn").disabled = false;
    }
  });
})();
