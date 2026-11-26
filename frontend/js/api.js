// Capa de acceso a datos. app.js solo usa window.API; aquí se decide si es real o simulado.
// Formatos de respuesta (iguales en modo real y mock):
//   login  -> { id, anon_id }
//   lad    -> { estudiante:{id,anon_id}, course_id,
//               resumen:{promedio_quizzes, quizzes_completados, scorm_completados, scorm_iniciados, tiempo_total_min, nota_max},
//               quizzes:[{quiz_id, nombre, intentos, mejor_nota, minutos, completado}],
//               scorm:[{scorm_id, nombre, intentos, minutos, puntaje, aciertos, total, completado}] }
//               intentos_scorm:[{scorm_id,nombre,intento,estado,segundos,key,pantalla,answers,results,fecha}],
//               intentos_quiz:[{quiz_id,nombre,intento,estado,nota,nota_maxima,minutos,fecha}]
//   metas  -> { meta_nota_porcentaje, meta_minutos_semanales }
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
    login: function (id, courseId) { return http("POST", "/api/login", { estudiante_id: Number(id), course_id: Number(courseId) }); },
    lad: function (id, courseId) { return http("GET", "/api/lad/" + id + "?course_id=" + encodeURIComponent(courseId)); },
    guardarMetas: function (id, courseId, nota, minutos) { return http("PUT", "/api/metas", { estudiante_id: Number(id), course_id: Number(courseId), meta_nota_porcentaje: Number(nota), meta_minutos_semanales: Number(minutos) }); },
    chat: function (id, courseId, mensaje, sessionId) { return http("POST", "/api/chat", { estudiante_id: Number(id), course_id: Number(courseId), mensaje: mensaje, session_id: sessionId || null }); },
    historial: function (id, courseId) { return http("GET", "/api/chat/historial?estudiante_id=" + encodeURIComponent(id) + "&course_id=" + encodeURIComponent(courseId)); }
  };

  // ---------- Modo de ejemplo (datos reproducibles a partir del ID) ----------
  function rng(seed) { var s = seed * 9301 + 49297; return function () { s = (s * 9301 + 49297) % 233280; return s / 233280; }; }
  var sleep = function (ms) { return new Promise(function (r) { setTimeout(r, ms); }); };
  var cache = {};

  // Datos de ejemplo con la misma forma que devuelve /api/lad (intentos por actividad).
  function mockLad(id) {
    if (cache[id]) return cache[id];
    var sd = function (key, pantalla, ans, res) { return { key: key, pantalla: pantalla, answers: ans, results: res }; };
    var scormI = [], quizI = [];
    var S = function (sid, nom, n, est, seg, d, fecha) { scormI.push({ scorm_id: sid, nombre: nom, intento: n, estado: est, segundos: seg, key: d.key, pantalla: d.pantalla, answers: d.answers, results: d.results, fecha: fecha }); };
    var Q = function (qid, nom, n, nota, max, min, fecha) { quizI.push({ quiz_id: qid, nombre: nom, intento: n, estado: "finished", nota: nota, nota_maxima: max, minutos: min, fecha: fecha }); };
    var N70 = "SCORM 70 · Álgebra de derivadas", N72 = "SCORM 72 · Regla de la cadena";
    var k70 = "oev-guia01-algebra-derivadas/5", k72 = "oev-guia02-regla-cadena/2";
    if (Number(id) === 1) {
      S(70, N70, 1, "incomplete", 60, sd(k70, "cierre", {}, {}), "2026-11-19 04:10:54");
      Q(19, "Quiz 19 · Eval. formativa álgebra de derivadas", 1, 1.0, 4.0, 0.85, "2026-11-19 04:12:30");
    } else {
      S(70, N70, 1, "completed", 180, sd(k70, "cierre",
        { "q-lineal": "resta-correcta", "q-constante": "constante-correcta", "q-producto": "leibniz-correcta", "q-cociente": "cociente-derivadas", "q-trig": "cociente-derivadas" },
        { "q-lineal": true, "q-constante": true, "q-producto": true, "q-cociente": false, "q-trig": false }), "2026-11-19 04:00:53");
      S(70, N70, 2, "completed", 80, sd(k70, "cierre",
        { "q-lineal": "resta-correcta", "q-constante": "constante-correcta", "q-producto": "leibniz-correcta", "q-cociente": "division-correcta", "q-trig": "regla-division" },
        { "q-lineal": true, "q-constante": true, "q-producto": true, "q-cociente": true, "q-trig": true }), "2026-11-19 04:04:20");
      S(72, N72, 1, "completed", 240, sd(k72, "cierre",
        { "q-cadena-u": "interna-correcta", "q-cadena-compuesta": "sin-derivada-interna", "q-cadena-trig": "cadena-trig-correcta", "q-cadena-exp": "sin-derivada-interna" },
        { "q-cadena-u": true, "q-cadena-compuesta": false, "q-cadena-trig": true, "q-cadena-exp": false }), "2026-11-19 04:14:10");
      S(72, N72, 2, "completed", 195, sd(k72, "cierre",
        { "q-cadena-u": "interna-correcta", "q-cadena-compuesta": "sin-derivada-interna", "q-cadena-trig": "cadena-trig-correcta", "q-cadena-exp": "cadena-exp-correcta" },
        { "q-cadena-u": true, "q-cadena-compuesta": false, "q-cadena-trig": true, "q-cadena-exp": true }), "2026-11-19 04:18:45");
      Q(19, "Quiz 19 · Eval. formativa álgebra de derivadas", 1, 2.0, 4.0, 1.12, "2026-11-19 04:10:57");
      Q(20, "Quiz 20 · Eval. formativa regla de la cadena", 1, 3.0, 5.0, 6.40, "2026-11-19 04:26:12");
      Q(20, "Quiz 20 · Eval. formativa regla de la cadena", 2, 4.5, 5.0, 8.20, "2026-11-19 04:36:05");
    }
    // Agregación equivalente a la del backend
    var scorm = {}, quizzes = {};
    scormI.forEach(function (a) {
      var s = scorm[a.scorm_id] || (scorm[a.scorm_id] = { scorm_id: a.scorm_id, nombre: a.nombre, intentos: 0, segundos: 0, puntaje: 0 });
      var v = Object.keys(a.results).map(function (k) { return a.results[k]; });
      s.intentos++; s.segundos += a.segundos; s.completado = a.estado === "completed";
      s.aciertos = v.filter(Boolean).length; s.total = v.length;
    });
    quizI.forEach(function (a) {
      var q = quizzes[a.quiz_id] || (quizzes[a.quiz_id] = { quiz_id: a.quiz_id, nombre: a.nombre, intentos: 0, minutos: 0, mejor_nota: 0, completado: false });
      q.intentos++; q.minutos += a.minutos; q.mejor_nota = Math.max(q.mejor_nota, a.nota); q.completado = true;
    });
    var scormL = Object.keys(scorm).map(function (k) { var s = scorm[k]; return { scorm_id: s.scorm_id, nombre: s.nombre, intentos: s.intentos, minutos: Math.round(s.segundos / 60), puntaje: 0, aciertos: s.aciertos, total: s.total, completado: s.completado }; });
    var quizL = Object.keys(quizzes).map(function (k) { var q = quizzes[k]; return { quiz_id: q.quiz_id, nombre: q.nombre, intentos: q.intentos, mejor_nota: q.mejor_nota, minutos: Math.round(q.minutos), completado: q.completado }; });
    var hechos = quizL.filter(function (q) { return q.completado; });
    var prom = hechos.length ? hechos.reduce(function (a, q) { return a + q.mejor_nota; }, 0) / hechos.length : 0;
    var sum = function (arr) { return arr.reduce(function (a, x) { return a + x.minutos; }, 0); };
    var total = sum(scormL) + sum(quizL);
    cache[id] = {
      estudiante: { id: Number(id), anon_id: "EST-" + String(id).padStart(3, "0") },
      course_id: 5,
      resumen: { promedio_quizzes: Math.round(prom * 10) / 10, quizzes_completados: hechos.length, quizzes_total: quizL.length,
        scorm_completados: scormL.filter(function (s) { return s.completado; }).length, scorm_iniciados: scormL.length,
        tiempo_scorm_min: sum(scormL), tiempo_total_min: total, tiempo_semana_min: total, progreso: 0, riesgo: "medio",
        nota_max: 7, meta_nota_porcentaje: 70, meta_minutos_semanales: 60 },
      quizzes: quizL, scorm: scormL, intentos_scorm: scormI, intentos_quiz: quizI
    };
    return cache[id];
  }
  function mockReply(id, t) {
    var d = mockLad(id), s = t.toLowerCase();
    var hechos = d.quizzes.filter(function (q) { return q.completado; });
    if (!hechos.length) hechos = [{ nombre: "cuestionario", mejor_nota: 0 }];
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
    guardarMetas: async function (id, c, n, m) { await sleep(150); return { meta_nota_porcentaje: n, meta_minutos_semanales: m }; },
    chat: async function (id, courseId, m) { await sleep(900); var r = mockReply(id, m); return { respuesta: r[1], fase: r[0], juez: "aprobado" }; },
    historial: async function () { return []; }
  };

  window.API = C.USE_MOCK ? mock : real;
})();
