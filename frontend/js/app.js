(function () {
  var $ = function (id) { return document.getElementById(id); };
  // Las claves coinciden con las fases que devuelve el clasificador del backend (nodes.py)
  var FASES = [
    { k: "planificacion", n: "Planificación", d: "Metas y estrategia" },
    { k: "monitoreo", n: "Monitoreo", d: "Seguimiento y desempeño" },
    { k: "reflexion", n: "Reflexión", d: "Qué ajustar" }
  ];
  var estId = null, fase = "indefinida";

  var fmt = function (n) { return (Math.round(n * 10) / 10).toFixed(1).replace(".", ","); };
  function esc(x) { return String(x).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function rich(x) { return esc(x).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/\n/g, "<br>"); }
  function nombreFase(k) { var f = FASES.filter(function (x) { return x.k === k; })[0]; return f ? f.n : ""; }

  // ---------- LAD ----------
  function kpi(v, l) { return '<div class="kpi"><b>' + v + "</b><small>" + l + "</small></div>"; }
  function dur(min) { min = Math.round(min); return min >= 60 ? Math.floor(min / 60) + " h " + (min % 60) + " min" : min + " min"; }
  function plural(n, a, b) { return n + " " + (n === 1 ? a : b); }

  function renderLad(d) {
    var r = d.resumen, max = r.nota_max || 7;
    $("who").textContent = d.estudiante.anon_id;
    $("title").textContent = "Estudiante " + d.estudiante.id;
    $("kpis").innerHTML =
      kpi(r.scorm_completados + "/" + r.scorm_iniciados, "Material interactivo completado") +
      kpi(String(r.quizzes_completados), "Cuestionarios completados") +
      kpi(r.quizzes_completados ? fmt(r.promedio_quizzes) : "–", "Promedio en cuestionarios") +
      kpi(dur(r.tiempo_total_min), "Tiempo total de estudio");

    // Gráfico de notas (solo cuestionarios completados)
    var hechos = d.quizzes.filter(function (q) { return q.completado; });
    $("escala").textContent = "Escala 0 a " + max;
    if (!hechos.length) {
      $("chartWrap").innerHTML = '<div class="empty">Aún no hay cuestionarios completados.</div>';
    } else {
      var bars = hechos.map(function (q) {
        return '<div class="bar' + (q.mejor_nota < max * 0.57 ? " low" : "") + '" style="height:' + Math.min(100, q.mejor_nota / max * 100) + '%"><span>' + fmt(q.mejor_nota) + "</span></div>";
      }).join("");
      var lab = hechos.map(function (q) { return "<span>Q" + q.quiz_id + "</span>"; }).join("");
      $("chartWrap").innerHTML =
        '<div class="chart"><div class="yaxis"><span>' + max + "</span><span>" + Math.round(max * .75) + "</span><span>" + Math.round(max / 2) + "</span><span>" + Math.round(max / 4) + "</span><span>0</span></div>" +
        '<div class="plot">' + bars + "</div></div>" + '<div class="xaxis"><span></span><div>' + lab + "</div></div>";
    }

    // Tiempo por actividad
    var acts = d.scorm.map(function (s) { return { n: s.nombre, m: s.minutos, q: false }; })
      .concat(d.quizzes.map(function (q) { return { n: q.nombre, m: q.minutos, q: true }; }));
    var mx = Math.max.apply(null, acts.map(function (a) { return a.m; }).concat([1]));
    $("hbars").innerHTML = acts.length ? acts.map(function (a) {
      return '<div class="hb"><span title="' + esc(a.n) + '">' + esc(a.n) + '</span><span class="track"><span class="fill' + (a.q ? " q" : "") + '" style="width:' + (a.m / mx * 100) + '%"></span></span><span class="v">' + a.m + "</span></div>";
    }).join("") : '<div class="empty">Aún no hay actividad registrada.</div>';

    // Material interactivo
    $("scormTotal").textContent = dur(d.scorm.reduce(function (a, s) { return a + s.minutos; }, 0)) + " en total";
    $("scorm").innerHTML = d.scorm.length ? d.scorm.map(function (s) {
      var res = s.total ? "<b>" + s.aciertos + " de " + s.total + "</b><small>preguntas correctas</small>" : "<b>" + Math.round(s.puntaje) + "%</b><small>puntaje</small>";
      return '<div class="act"><div class="t"><div>' + esc(s.nombre) + "</div><small>" + dur(s.minutos) + " · " + plural(s.intentos, "intento", "intentos") + '</small></div><div class="res">' + res + '</div><span class="pill' + (s.completado ? " done" : "") + '">' + (s.completado ? "Completado" : "En progreso") + "</span></div>";
    }).join("") : '<div class="empty">Aún no hay actividad en material interactivo.</div>';

    // Cuestionarios
    $("quizTotal").textContent = dur(d.quizzes.reduce(function (a, q) { return a + q.minutos; }, 0)) + " en total";
    $("quizzes").innerHTML = d.quizzes.length ? d.quizzes.map(function (q) {
      var res = q.completado ? "<b>" + fmt(q.mejor_nota) + " de " + max + "</b><small>mejor nota</small>" : "<b>–</b><small>sin nota</small>";
      return '<div class="act"><div class="t"><div>' + esc(q.nombre) + "</div><small>" + dur(q.minutos) + " · " + plural(q.intentos, "intento", "intentos") + '</small></div><div class="res">' + res + '</div><span class="pill' + (q.completado ? " done" : " none") + '">' + (q.completado ? "Completado" : "Sin completar") + "</span></div>";
    }).join("") : '<div class="empty">Aún no hay cuestionarios rendidos.</div>';
    renderFases();
  }
  function renderFases() {
    $("phases").innerHTML = FASES.map(function (f) {
      return '<div class="phase' + (f.k === fase ? " on" : "") + '"><b>' + f.n + "</b><small>" + f.d + "</small></div>";
    }).join("");
  }

  // ---------- Chat ----------
  function add(cls, html) {
    var el = document.createElement("div"); el.className = "m " + cls; el.innerHTML = html;
    $("msgs").appendChild(el); $("msgs").scrollTop = $("msgs").scrollHeight; return el;
  }
  function botHtml(texto, f) { var n = nombreFase(f); return (n ? '<span class="tag">' + n + "</span>" : "") + rich(texto); }

  async function send(text) {
    text = text.trim(); if (!text) return;
    add("me", esc(text)); $("msg").value = ""; $("sendBtn").disabled = true;
    var typing = add("bot", '<span class="dots"><i></i><i></i><i></i></span>');
    try {
      var out = await API.chat(estId, text);
      fase = out.fase; renderFases();
      typing.innerHTML = botHtml(out.respuesta, out.fase);
    } catch (e) {
      typing.innerHTML = "No pude responder en este momento. Intenta de nuevo en unos segundos.";
    }
    $("sendBtn").disabled = false; $("msgs").scrollTop = $("msgs").scrollHeight;
  }

  async function startChat() {
    $("msgs").innerHTML = ""; fase = "indefinida"; renderFases();
    var hist = [];
    try { hist = await API.historial(estId); } catch (e) {}
    if (hist.length) {
      hist.forEach(function (h) { add(h.rol === "user" ? "me" : "bot", h.rol === "user" ? esc(h.texto) : botHtml(h.texto, h.fase)); });
    } else {
      add("bot", "Hola. Soy tu tutor. No te daré respuestas directas: te haré preguntas para que analices tu propio avance. ¿Qué te gustaría revisar de tu panel?");
    }
    $("chips").innerHTML = ["¿Cómo me fue en los cuestionarios?", "¿Cuánto he estudiado?", "Quiero plantear una meta", "¿En qué preguntas me equivoqué?"]
      .map(function (c) { return '<button type="button" class="chip">' + c + "</button>"; }).join("");
  }

  // ---------- Eventos ----------
  $("chips").addEventListener("click", function (e) { if (e.target.classList.contains("chip")) send(e.target.textContent); });
  $("composer").addEventListener("submit", function (e) { e.preventDefault(); send($("msg").value); });
  $("loginForm").addEventListener("submit", async function (e) {
    e.preventDefault();
    var v = $("uid").value.trim();
    if (!/^\d+$/.test(v)) { $("err").textContent = "Ingresa un ID numérico, por ejemplo 3."; return; }
    $("err").textContent = ""; $("loginBtn").disabled = true;
    try {
      await API.login(v);
      var lad = await API.lad(v);
      estId = v; renderLad(lad); await startChat();
      $("login").hidden = true; $("app").hidden = false; window.scrollTo(0, 0);
    } catch (er) {
      $("err").textContent = /fetch|network/i.test(er.message) ? "No se pudo conectar con el servidor." : er.message;
    }
    $("loginBtn").disabled = false;
  });
  $("logout").addEventListener("click", function () {
    estId = null; $("app").hidden = true; $("login").hidden = false; $("uid").value = ""; $("uid").focus();
  });
})();
