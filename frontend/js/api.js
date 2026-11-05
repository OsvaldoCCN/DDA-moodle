// Capa de acceso a datos. app.js solo usa window.API; aquí se decide si es real o simulado.
// Formatos de respuesta (iguales en modo real y mock):
//   login  -> { id, anon_id }
//   lad    -> { estudiante:{id,anon_id},
//               resumen:{promedio_quizzes, quizzes_completados, scorm_completados, scorm_iniciados, tiempo_total_min, nota_max},
//               quizzes:[{quiz_id, nombre, intentos, mejor_nota, minutos, completado}],
//               scorm:[{scorm_id, nombre, intentos, minutos, puntaje, aciertos, total, completado}] }
//   chat   -> { respuesta, fase, juez }
//   historial -> [{ rol:"user"|"bot", texto, fase }]
(function () {
  var C = window.CONFIG;

  async function http(method, path, body) {
    var res = await fetch(C.API_URL + path, {
      method: method,
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined
    });
    if (!res.ok) {
      var detalle = "Error " + res.status;
      try { detalle = (await res.json()).detail || detalle; } catch (e) {}
      throw new Error(detalle);
    }
    return res.json();
  }

  var real = {
    login: function (id) { return http("POST", "/api/login", { estudiante_id: id }); },
    lad: function (id) { return http("GET", "/api/lad/" + id); },
    chat: function (id, mensaje) { return http("POST", "/api/chat", { estudiante_id: id, mensaje: mensaje }); },
    historial: function (id) { return http("GET", "/api/historial/" + id); }
  };

  // ---------- Modo de ejemplo (datos reproducibles a partir del ID) ----------
  function rng(seed) { var s = seed * 9301 + 49297; return function () { s = (s * 9301 + 49297) % 233280; return s / 233280; }; }
  var sleep = function (ms) { return new Promise(function (r) { setTimeout(r, ms); }); };
  var cache = {};

  function mockLad(id) {
    if (cache[id]) return cache[id];
    var r = rng(parseInt(id, 10) + 7), i;
    var quizzes = [];
    for (i = 1; i <= 5; i++) {
      var hecho = i <= 4 || r() > 0.5;
      quizzes.push({ quiz_id: i, nombre: "Quiz Unidad " + i, intentos: hecho ? 1 + Math.floor(r() * 3) : 1,
        mejor_nota: hecho ? Math.round((3 + r() * 3.8) * 10) / 10 : 0, minutos: Math.round(6 + r() * 18), completado: hecho });
    }
    var nombres = ["Unidad 1: Introducción", "Unidad 2: Estrategias de estudio", "Unidad 3: Práctica guiada", "Unidad 4: Casos aplicados"];
    var scorm = nombres.map(function (n, k) {
      var total = 8 + Math.floor(r() * 5), ok = Math.round(total * (0.45 + r() * 0.55)), done = r() > 0.3;
      return { scorm_id: k + 1, nombre: n, intentos: 1 + Math.floor(r() * 2), minutos: Math.round(10 + r() * 50),
        puntaje: Math.round(ok / total * 100), aciertos: ok, total: total, completado: done };
    });
    var hechos = quizzes.filter(function (q) { return q.completado; });
    var prom = hechos.reduce(function (a, q) { return a + q.mejor_nota; }, 0) / hechos.length;
    var sum = function (arr) { return arr.reduce(function (a, x) { return a + x.minutos; }, 0); };
    cache[id] = {
      estudiante: { id: Number(id), anon_id: "anon_" + String(id).padStart(4, "0") },
      resumen: { promedio_quizzes: Math.round(prom * 10) / 10, quizzes_completados: hechos.length,
        scorm_completados: scorm.filter(function (s) { return s.completado; }).length, scorm_iniciados: scorm.length,
        tiempo_total_min: sum(scorm) + sum(quizzes), nota_max: 7 },
      quizzes: quizzes, scorm: scorm
    };
    return cache[id];
  }
  function mockReply(id, t) {
    var d = mockLad(id), s = t.toLowerCase();
    var hechos = d.quizzes.filter(function (q) { return q.completado; });
    var peor = hechos.slice().sort(function (a, b) { return a.mejor_nota - b.mejor_nota; })[0];
    var n = function (x) { return String(x).replace(".", ","); };
    if (/nota|quiz|cuestionario|calific/.test(s)) return ["monitoreo", "Tu nota más baja fue en el " + peor.nombre + " (" + n(peor.mejor_nota) + "). ¿Qué crees que pasó ahí que no pasó en tu mejor cuestionario?"];
    if (/scorm|tiempo|estudi|material/.test(s)) return ["monitoreo", "Llevas " + d.resumen.tiempo_total_min + " minutos entre material y cuestionarios. ¿Seguiste un plan o fuiste avanzando según el momento?"];
    if (/meta|plan|organiz|objetivo/.test(s)) return ["planificacion", "Antes de proponerte algo, ¿qué te gustaría lograr esta semana y cómo sabrías que lo lograste?"];
    if (/ayuda|dif[ií]cil|complic|error|equivoc/.test(s)) return ["reflexion", "Mirando tus resultados, ¿en qué preguntas del material interactivo te equivocaste más y qué cambiarías al estudiarlas?"];
    return ["reflexion", "Interesante. ¿Qué dato de tu panel te llamó más la atención y por qué?"];
  }
  var mock = {
    login: async function (id) { await sleep(250); return mockLad(id).estudiante; },
    lad: async function (id) { await sleep(250); return mockLad(id); },
    chat: async function (id, m) { await sleep(900); var r = mockReply(id, m); return { respuesta: r[1], fase: r[0], juez: "aprobado" }; },
    historial: async function () { return []; }
  };

  window.API = C.USE_MOCK ? mock : real;
})();
