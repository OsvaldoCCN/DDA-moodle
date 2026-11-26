(function () {
  var $ = function (id) { return document.getElementById(id); };

  var FASES = [
    { k: "planificacion", n: "Planeación" },
    { k: "monitoreo", n: "Ejecución" },
    { k: "reflexion", n: "Autorreflexión" }
  ];
  var THEME = {
    bg: "#121A21", ink: "#E6EBEE", accent: "#B8923A",
    inkSoft: "rgba(230, 235, 238, 0.62)", line: "rgba(230, 235, 238, 0.16)",
    mono: '"IBM Plex Mono", ui-monospace, monospace', body: '"IBM Plex Sans", system-ui, sans-serif'
  };

  var estId = null, courseId = null;
  var data = null, scormSel = null;
  var chartEvol = null, chartScatter = null, chartTiempo = null;

  // ---------- Utilidades ----------
  function esc(x) {
    return String(x == null ? "" : x).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function rich(x) {
    var lines = esc(x).split("\n");
    var html = [], inList = false;
    lines.forEach(function (line) {
      var trimmed = line.trim();
      var bullet = /^[-*•]\s+(.+)/.exec(trimmed);
      var fmt = function (s) {
        return s
          .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
          .replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');
      };
      if (bullet) {
        if (!inList) { html.push('<ul class="chat-list">'); inList = true; }
        html.push("<li>" + fmt(bullet[1]) + "</li>");
      } else {
        if (inList) { html.push("</ul>"); inList = false; }
        if (trimmed === "") html.push("<br>");
        else html.push("<span>" + fmt(line) + "</span><br>");
      }
    });
    if (inList) html.push("</ul>");
    return html.join("").replace(/(<br>)+$/, "");
  }

  function nombreFase(k) {
    var f = FASES.filter(function (x) { return x.k === k; })[0];
    return f ? f.n : "";
  }

  function pct(n, d) { return d > 0 ? Math.round(n / d * 100) : 0; }

  // Formato unificado de tiempo: <60s -> segundos; <3600s -> u.d min; >=3600s -> u.d h
  function fmtTiempo(segundos) {
    var s = Math.max(0, Number(segundos) || 0);
    if (s < 60) return Math.round(s) + " s";
    if (s < 3600) return (s / 60).toFixed(1) + " min";
    return (s / 3600).toFixed(1) + " h";
  }

  // Divide nombres largos en varias líneas para etiquetas limpias en Chart.js
  function wrapLabel(str, maxLen) {
    var words = String(str || "").split(/\s+/);
    var lines = [], cur = "";
    words.forEach(function (w) {
      if (!cur) { cur = w; }
      else if ((cur + " " + w).length <= maxLen) { cur += " " + w; }
      else { lines.push(cur); cur = w; }
    });
    if (cur) lines.push(cur);
    return lines.length > 1 ? lines : (lines[0] || "");
  }

  function metrics(results) {
    var v = Object.keys(results || {}).map(function (k) { return results[k]; });
    var ok = v.filter(function (x) { return x === true; }).length;
    return { ok: ok, total: v.length, pct: pct(ok, v.length) };
  }

  function fechaHtml(f) {
    var m = /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})/.exec(f || "");
    if (!m) return esc(f);
    return '<div class="date-cell"><b>' + m[3] + "/" + m[2] + "/" + m[1].slice(2) + "</b><span>" + m[4] + ":" + m[5] + "</span></div>";
  }

  function quizPct(a) { return a.nota_maxima > 0 ? Math.round(a.nota / a.nota_maxima * 100) : 0; }

  function lastBy(arr, key) {
    var m = {};
    arr.forEach(function (a) { if (!m[a[key]] || a.intento >= m[a[key]].intento) m[a[key]] = a; });
    return Object.keys(m).map(function (k) { return m[k]; });
  }

  // ---------- KPIs ----------
  function renderKPIs() {
    var sc = data.intentos_scorm, qz = data.intentos_quiz;
    var scormSec = sc.reduce(function (a, r) { return a + (Number(r.segundos) || 0); }, 0);
    var quizSec = qz.reduce(function (a, r) { return a + (Number(r.minutos) || 0) * 60; }, 0);
    var totalSec = scormSec + quizSec;

    $("kpi-total-time").textContent = fmtTiempo(totalSec);
    $("kpi-attempts-summary").textContent = "en " + (sc.length + qz.length) + " intento(s) registrados";
    $("kpi-scorm-time").textContent = fmtTiempo(scormSec);
    $("kpi-quiz-time").textContent = fmtTiempo(quizSec);

    renderPerformance();

    // Avance
    var all = data.scorm.length + data.quizzes.length;
    var done = data.scorm.filter(function (s) { return s.completado; }).length + data.quizzes.filter(function (q) { return q.completado; }).length;
    $("kpi-avance").textContent = done + " / " + all;

    // Punto de retorno: módulos cuyo último intento quedó incompleto
    var pend = lastBy(sc, "scorm_id").filter(function (a) { return (a.estado || "").toLowerCase() === "incomplete"; });
    var box = $("return-point-container");
    if (pend.length) {
      box.innerHTML = pend.slice(0, 2).map(function (a, i) {
        var recurso = a.key || a.nombre;
        return '<div class="return-alert"' + (i ? ' style="margin-top:6px"' : "") + ">" +
          '<div style="display:flex; justify-content:space-between; align-items:center; gap:6px;"><strong style="color:var(--accent);">Punto de retorno pendiente</strong><span class="pill">incomplete</span></div>' +
          '<div>Recurso: <span class="mono">' + esc(recurso) + "</span></div>" +
          '<div style="display:flex; justify-content:space-between; align-items:center; gap:8px; margin-top:2px;">' +
          '<span>Pantalla: <span class="mono" style="color:var(--accent);">' + esc(a.pantalla || "-") + "</span></span>" +
          '<button type="button" class="btn-ghost" data-return="' + i + '">Consultar tutor →</button></div></div>';
      }).join("");
      box._pend = pend;
    } else {
      box.innerHTML = '<div class="return-ok">Todos los módulos iniciados registran estado <span class="mono" style="color:var(--ink);">completed</span>.</div>';
      box._pend = [];
    }
  }

  function renderPerformance() {
    var scBest = {}, qzBest = {};
    var scFirst = {}, scLast = {}, qzFirst = {}, qzLast = {};

    data.intentos_scorm.forEach(function (a) {
      var m = metrics(a.results);
      if (m.total <= 0) return;
      var p = m.pct;
      if (scBest[a.scorm_id] == null || p > scBest[a.scorm_id]) scBest[a.scorm_id] = p;
      if (!scFirst[a.scorm_id] || a.intento < scFirst[a.scorm_id].intento) scFirst[a.scorm_id] = { intento: a.intento, pct: p };
      if (!scLast[a.scorm_id] || a.intento > scLast[a.scorm_id].intento) scLast[a.scorm_id] = { intento: a.intento, pct: p };
    });

    data.intentos_quiz.forEach(function (a) {
      if (!(a.nota_maxima > 0)) return;
      var p = quizPct(a);
      if (qzBest[a.quiz_id] == null || p > qzBest[a.quiz_id]) qzBest[a.quiz_id] = p;
      if (!qzFirst[a.quiz_id] || a.intento < qzFirst[a.quiz_id].intento) qzFirst[a.quiz_id] = { intento: a.intento, pct: p };
      if (!qzLast[a.quiz_id] || a.intento > qzLast[a.quiz_id].intento) qzLast[a.quiz_id] = { intento: a.intento, pct: p };
    });

    var scVals = Object.keys(scBest).map(function (k) { return scBest[k]; });
    var qzVals = Object.keys(qzBest).map(function (k) { return qzBest[k]; });
    var allVals = scVals.concat(qzVals);

    var avgAll = allVals.length ? Math.round(allVals.reduce(function (a, b) { return a + b; }, 0) / allVals.length) : null;
    var avgSc = scVals.length ? Math.round(scVals.reduce(function (a, b) { return a + b; }, 0) / scVals.length) : null;
    var avgQz = qzVals.length ? Math.round(qzVals.reduce(function (a, b) { return a + b; }, 0) / qzVals.length) : null;

    // Evolución promedio entre el primer y último intento en actividades repetidas
    var deltas = [];
    Object.keys(scFirst).forEach(function (k) {
      if (scLast[k].intento > scFirst[k].intento) deltas.push(scLast[k].pct - scFirst[k].pct);
    });
    Object.keys(qzFirst).forEach(function (k) {
      if (qzLast[k].intento > qzFirst[k].intento) deltas.push(qzLast[k].pct - qzFirst[k].pct);
    });

    $("kpi-perf-avg").textContent = avgAll != null ? avgAll + "%" : "—";
    $("kpi-perf-sub").textContent = allVals.length
      ? "mejor logro en " + allVals.length + " actividad(es) evaluada(s)"
      : "sin actividades evaluadas aún";
    $("kpi-perf-scorm").textContent = avgSc != null ? avgSc + "%" : "—";
    $("kpi-perf-quiz").textContent = avgQz != null ? avgQz + "%" : "—";

    if (deltas.length) {
      var avgDelta = Math.round(deltas.reduce(function (a, b) { return a + b; }, 0) / deltas.length);
      var sign = avgDelta > 0 ? "+" : "";
      $("kpi-perf-delta").textContent = sign + avgDelta + " pts (" + deltas.length + " act.)";
    } else {
      $("kpi-perf-delta").textContent = "Sin reintentos aún";
    }
  }

  // ---------- Gráficos ----------
  function renderCharts() {
    if (!window.Chart) return;
    var groups = {}, order = [];
    function put(key, nombre, intento, p, raw) {
      if (!groups[key]) { groups[key] = { full: nombre, tick: wrapLabel(nombre, 20), att: {} }; order.push(key); }
      groups[key].att[intento] = { pct: p, raw: raw };
    }
    data.intentos_scorm.forEach(function (a) {
      var m = metrics(a.results);
      put("s" + a.scorm_id, a.nombre, a.intento, m.pct, m.ok + "/" + m.total + " aciertos");
    });
    data.intentos_quiz.forEach(function (a) {
      put("q" + a.quiz_id, a.nombre, a.intento, quizPct(a), a.nota.toFixed(1) + " / " + a.nota_maxima.toFixed(1));
    });
    var items = order.map(function (k) { return groups[k]; });
    var maxInt = Math.min(5, items.reduce(function (m, g) { return Math.max(m, Math.max.apply(null, Object.keys(g.att).map(Number))); }, 1));
    var datasets = [];
    for (var n = 1; n <= maxInt; n++) {
      (function (n) {
        var alpha = maxInt === 1 ? 1 : 0.3 + 0.7 * (n - 1) / (maxInt - 1);
        datasets.push({
          label: "Intento " + n,
          data: items.map(function (g) { return g.att[n] ? g.att[n].pct : null; }),
          backgroundColor: "rgba(184, 146, 58, " + alpha.toFixed(2) + ")",
          borderColor: THEME.accent, borderWidth: 1.5, borderRadius: 4, maxBarThickness: 34
        });
      })(n);
    }
    var tooltip = {
      backgroundColor: THEME.bg, borderColor: THEME.accent, borderWidth: 1,
      titleColor: THEME.accent, bodyColor: THEME.ink,
      titleFont: { family: THEME.body, size: 12 }, bodyFont: { family: THEME.mono, size: 12 }
    };
    var legend = { labels: { color: THEME.inkSoft, boxWidth: 12, font: { family: THEME.body, size: 12 } } };

    if (chartEvol) chartEvol.destroy();
    chartEvol = new Chart($("chart-evolucion").getContext("2d"), {
      type: "bar",
      data: { labels: items.map(function (g) { return g.tick; }), datasets: datasets },
      options: {
        responsive: true, maintainAspectRatio: false,
        scales: {
          y: {
            beginAtZero: true, max: 100, grid: { color: THEME.line }, border: { color: THEME.line },
            ticks: { color: THEME.inkSoft, font: { family: THEME.mono, size: 11 }, callback: function (v) { return v + "%"; } }
          },
          x: {
            grid: { display: false }, border: { color: THEME.line },
            ticks: { color: THEME.ink, font: { family: THEME.body, size: 11 }, maxRotation: 25, minRotation: 0 }
          }
        },
        plugins: {
          legend: legend,
          tooltip: Object.assign({}, tooltip, {
            callbacks: {
              title: function (c) { return items[c[0].dataIndex].full; },
              label: function (c) { var i = items[c.dataIndex].att[c.datasetIndex + 1]; return i ? "Intento " + (c.datasetIndex + 1) + ": " + i.pct + "% (" + i.raw + ")" : ""; }
            }
          })
        }
      }
    });

    var pS = data.intentos_scorm.map(function (a) {
      var m = metrics(a.results);
      return {
        x: Number((a.segundos / 60).toFixed(2)),
        y: m.pct,
        actividad: a.nombre,
        intento: a.intento,
        detalle: m.ok + "/" + m.total + " aciertos · " + fmtTiempo(a.segundos)
      };
    });
    var pQ = data.intentos_quiz.map(function (a) {
      return {
        x: Number(a.minutos.toFixed(2)),
        y: quizPct(a),
        actividad: a.nombre,
        intento: a.intento,
        detalle: a.nota.toFixed(1) + " / " + a.nota_maxima.toFixed(1) + " · " + fmtTiempo(a.minutos * 60)
      };
    });
    var axisTitle = function (t) { return { display: true, text: t, color: THEME.inkSoft, font: { family: THEME.body, size: 11 } }; };
    if (chartScatter) chartScatter.destroy();
    chartScatter = new Chart($("chart-scatter").getContext("2d"), {
      type: "scatter",
      data: {
        datasets: [
          { label: "Material (círculo)", data: pS, backgroundColor: "rgba(184, 146, 58, 0.36)", borderColor: THEME.accent, borderWidth: 1.5, pointRadius: 6, pointHoverRadius: 8 },
          { label: "Cuestionario (rombo)", data: pQ, backgroundColor: THEME.accent, borderColor: THEME.ink, borderWidth: 1, pointStyle: "rectRot", pointRadius: 7, pointHoverRadius: 9 }
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        scales: {
          x: { beginAtZero: true, grid: { color: THEME.line }, border: { color: THEME.line }, title: axisTitle("Tiempo invertido (min)"), ticks: { color: THEME.inkSoft, font: { family: THEME.mono, size: 11 } } },
          y: {
            beginAtZero: true, max: 105, grid: { color: THEME.line }, border: { color: THEME.line }, title: axisTitle("Logro (%)"),
            ticks: { color: THEME.inkSoft, font: { family: THEME.mono, size: 11 }, callback: function (v) { return v <= 100 ? v + "%" : ""; } }
          }
        },
        plugins: {
          legend: legend,
          tooltip: Object.assign({}, tooltip, {
            bodyFont: { family: THEME.mono, size: 11.5 }, callbacks: {
              title: function (c) { return c[0].raw.actividad + " (Intento " + c[0].raw.intento + ")"; },
              label: function (c) { return "Logro: " + c.raw.y + "% | " + c.raw.detalle; }
            }
          })
        }
      }
    });

    // Tiempo por actividad (horizontal) con nombres reales
    var tAct = [], tSc = {}, tQz = {};
    data.intentos_scorm.forEach(function (a) {
      if (!tSc[a.scorm_id]) tSc[a.scorm_id] = { nombre: a.nombre, seg: 0 };
      tSc[a.scorm_id].seg += Number(a.segundos) || 0;
    });
    data.intentos_quiz.forEach(function (a) {
      if (!tQz[a.quiz_id]) tQz[a.quiz_id] = { nombre: a.nombre, seg: 0 };
      tQz[a.quiz_id].seg += (Number(a.minutos) || 0) * 60;
    });
    Object.keys(tSc).forEach(function (k) { tAct.push({ full: tSc[k].nombre, tick: wrapLabel(tSc[k].nombre, 24), seg: tSc[k].seg, q: false }); });
    Object.keys(tQz).forEach(function (k) { tAct.push({ full: tQz[k].nombre, tick: wrapLabel(tQz[k].nombre, 24), seg: tQz[k].seg, q: true }); });

    if (chartTiempo) chartTiempo.destroy();
    chartTiempo = new Chart($("chart-tiempo").getContext("2d"), {
      type: "bar",
      data: {
        labels: tAct.map(function (a) { return a.tick; }),
        datasets: [{
          data: tAct.map(function (a) { return Number((a.seg / 60).toFixed(2)); }),
          backgroundColor: tAct.map(function (a) { return a.q ? "rgba(184, 146, 58, 0.12)" : THEME.accent; }),
          borderColor: THEME.accent, borderWidth: 1.5, borderRadius: 4, maxBarThickness: 22
        }]
      },
      options: {
        indexAxis: "y", responsive: true, maintainAspectRatio: false,
        scales: {
          x: { beginAtZero: true, grid: { color: THEME.line }, border: { color: THEME.line }, title: axisTitle("Minutos"), ticks: { color: THEME.inkSoft, font: { family: THEME.mono, size: 11 } } },
          y: { grid: { display: false }, border: { color: THEME.line }, ticks: { color: THEME.ink, font: { family: THEME.body, size: 11 } } }
        },
        plugins: {
          legend: { display: false },
          tooltip: Object.assign({}, tooltip, {
            callbacks: {
              title: function (c) { return tAct[c[0].dataIndex].full; },
              label: function (c) { return "Tiempo acumulado: " + fmtTiempo(tAct[c.dataIndex].seg); }
            }
          })
        }
      }
    });
  }

  // ---------- Matriz pregunta × intento ----------
  function renderMatrix() {
    var ids = [];
    data.intentos_scorm.forEach(function (a) { if (ids.indexOf(a.scorm_id) < 0) ids.push(a.scorm_id); });
    var thead = $("matrix-head"), tbody = $("matrix-body"), sel = $("scorm-select");
    if (!ids.length) {
      sel.innerHTML = ""; thead.innerHTML = "";
      tbody.innerHTML = '<tr><td style="color:var(--soft); text-align:center; padding:18px;">Aún no hay intentos en material interactivo.</td></tr>';
      return;
    }
    if (ids.indexOf(scormSel) < 0) {
      var ultimos = lastBy(data.intentos_scorm, "scorm_id");
      var conError = ids.filter(function (id) {
        return ultimos.some(function (a) { var m = metrics(a.results); return a.scorm_id === id && m.ok < m.total; });
      });
      scormSel = (conError[0] != null) ? conError[0] : ids[0];
    }
    sel.innerHTML = ids.map(function (id) {
      var nombre = data.intentos_scorm.filter(function (a) { return a.scorm_id === id; })[0].nombre;
      return '<option value="' + id + '"' + (id === scormSel ? " selected" : "") + ">" + esc(nombre) + "</option>";
    }).join("");

    var parsed = data.intentos_scorm.filter(function (a) { return a.scorm_id === scormSel; })
      .sort(function (a, b) { return a.intento - b.intento; });
    var qids = [];
    parsed.forEach(function (p) { Object.keys(p.results || {}).forEach(function (q) { if (qids.indexOf(q) < 0) qids.push(q); }); });

    thead.innerHTML = "<tr><th>Pregunta</th>" +
      parsed.map(function (p) { return '<th style="text-align:center;">Intento ' + p.intento + "</th>"; }).join("") +
      "<th>Evolución</th></tr>";

    if (!qids.length) {
      var p0 = parsed[0];
      tbody.innerHTML = '<tr><td colspan="' + (parsed.length + 2) + '" style="color:var(--soft); text-align:center; padding:18px;">' +
        'Sin preguntas respondidas. Llegó a la pantalla <span class="mono" style="color:var(--accent);">' + esc(p0.pantalla || "-") + '</span> en <span class="mono">' + fmtTiempo(p0.segundos) + '</span> con estado <span class="mono">' + esc(p0.estado || "-") + "</span>.</td></tr>";
      return;
    }

    tbody.innerHTML = qids.map(function (qid, i) {
      var first = parsed[0], last = parsed[parsed.length - 1];
      var cells = parsed.map(function (p) {
        var r = (p.results || {})[qid];
        if (r === true) return '<td style="text-align:center;"><span class="mark-ok" title="Correcta">✓</span></td>';
        if (r === false) return '<td style="text-align:center;"><span class="mark-err" title="Incorrecta">✗</span></td>';
        return '<td style="text-align:center; color:var(--soft);">—</td>';
      }).join("");
      var a1 = (first.answers || {})[qid], aL = (last.answers || {})[qid];
      var ok1 = (first.results || {})[qid], okL = (last.results || {})[qid];
      var multi = parsed.length > 1, estado;
      if (multi && ok1 === false && okL === false && a1 === aL) estado = '<span class="pill persist">Error persistente</span>';
      else if (multi && ok1 === false && okL === true) estado = '<span class="pill">Corregida</span>';
      else if (multi && ok1 === true && okL === false) estado = '<span class="pill none">Retrocedió</span>';
      else if (okL === false) estado = '<span class="pill none">Incorrecta</span>';
      else estado = '<span style="color:var(--soft); font-size:12.5px;">Correcta</span>';
      return '<tr><td class="matrix-q" title="' + esc(qid) + '">P' + (i + 1) + "</td>" + cells + "<td>" + estado + "</td></tr>";
    }).join("");
  }

  // ---------- Bitácora ----------
  function renderLog() {
    var rows = data.intentos_scorm.map(function (a) {
      var m = metrics(a.results);
      return {
        fecha: a.fecha, tipo: "SCORM", actividad: a.nombre, intento: a.intento, estado: a.estado,
        resultado: m.total > 0 ? m.ok + " / " + m.total + " aciertos (" + m.pct + "%)" : "0 / 0 (pantalla: " + (a.pantalla || "-") + ")",
        tiempo: fmtTiempo(a.segundos)
      };
    }).concat(data.intentos_quiz.map(function (a) {
      return {
        fecha: a.fecha, tipo: "Quiz", actividad: a.nombre, intento: a.intento, estado: a.estado,
        resultado: a.nota.toFixed(1) + " / " + a.nota_maxima.toFixed(1) + " (" + quizPct(a) + "%)",
        tiempo: fmtTiempo(a.minutos * 60)
      };
    }));
    rows.sort(function (a, b) { return String(a.fecha).localeCompare(String(b.fecha)); });
    $("log-body").innerHTML = rows.length ? rows.map(function (r) {
      var est = (r.estado || "").toLowerCase();
      var done = est === "completed" || est === "finished" || est === "passed";
      return "<tr>" +
        "<td>" + fechaHtml(r.fecha) + "</td>" +
        '<td><span class="' + (r.tipo === "Quiz" ? "pill" : "pill none") + '">' + r.tipo + "</span></td>" +
        "<td>" + esc(r.actividad) + "</td>" +
        '<td class="mono" style="text-align:center;">#' + r.intento + "</td>" +
        '<td><span class="' + (done ? "pill done" : "pill") + '">' + esc(r.estado || "-") + "</span></td>" +
        '<td class="mono" style="font-size:12.5px;">' + esc(r.resultado) + "</td>" +
        '<td class="mono" style="font-size:12.5px; color:var(--soft); white-space:nowrap;">' + esc(r.tiempo) + "</td></tr>";
    }).join("") : '<tr><td colspan="7" class="empty" style="text-align:center;">Aún no hay intentos registrados.</td></tr>';
  }

  function renderLad(d) {
    data = d;
    d.intentos_scorm = d.intentos_scorm || [];
    d.intentos_quiz = d.intentos_quiz || [];
    $("who").textContent = "Curso " + (d.course_id != null ? d.course_id : courseId);
    renderKPIs(); renderCharts(); renderMatrix(); renderLog();
  }

  // ---------- Chat ----------
  function add(cls, html) {
    var el = document.createElement("div"); el.className = "m " + cls; el.innerHTML = html;
    $("msgs").appendChild(el); $("msgs").scrollTop = $("msgs").scrollHeight; return el;
  }
  function botHtml(texto, f) { var n = nombreFase(f); return (n ? '<span class="tag">' + n + "</span>" : "") + rich(texto); }

  function resetComposerHeight() {
    var ta = $("msg");
    ta.style.height = "auto";
  }

  var chatSessionId = null;

  async function send(text) {
    text = text.trim(); if (!text) return;
    add("me", esc(text).replace(/\n/g, "<br>"));
    $("msg").value = "";
    resetComposerHeight();
    $("sendBtn").disabled = true;
    var typing = add("bot", '<span class="dots"><i></i><i></i><i></i></span>');
    try {
      var out = await API.chat(estId, courseId, text, chatSessionId);
      typing.innerHTML = botHtml(out.respuesta, out.fase);
    } catch (e) {
      typing.innerHTML = "No pude responder en este momento. Intenta de nuevo en unos segundos.";
    }
    $("sendBtn").disabled = false; $("msgs").scrollTop = $("msgs").scrollHeight;
  }

  function startChat() {
    chatSessionId = "s_" + Date.now() + "_" + Math.random().toString(36).slice(2, 8);
    $("msgs").innerHTML = "";
    add("bot", "Hola. Soy tu tutor. No te daré respuestas directas: te haré preguntas para que analices tu propio avance. ¿Qué te gustaría revisar de tu panel?");
    $("chips").innerHTML = ["¿Cómo me fue en los cuestionarios?", "¿Cuánto he estudiado?", "¿En qué preguntas me equivoqué?", "¿Cómo puedo mejorar mi rendimiento?"]
      .map(function (c) { return '<button type="button" class="chip">' + c + "</button>"; }).join("");
  }

  // ---------- Eventos ----------
  $("chips").addEventListener("click", function (e) { if (e.target.classList.contains("chip")) send(e.target.textContent); });
  $("composer").addEventListener("submit", function (e) { e.preventDefault(); send($("msg").value); });
  $("msg").addEventListener("input", function () {
    this.style.height = "auto";
    this.style.height = Math.min(this.scrollHeight, 120) + "px";
  });
  $("msg").addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send(this.value);
    }
  });
  $("scorm-select").addEventListener("change", function (e) { scormSel = Number(e.target.value); renderMatrix(); });
  $("return-point-container").addEventListener("click", function (e) {
    var b = e.target.closest("[data-return]"); if (!b) return;
    var a = $("return-point-container")._pend[Number(b.dataset.return)];
    send("Mi intento en " + a.nombre + (a.key ? " (" + a.key + ")" : "") + " quedó en estado 'incomplete' en la pantalla '" + (a.pantalla || "-") + "'. ¿Cómo me recomiendas retomarlo?");
  });
  $("logout").addEventListener("click", function () { SESSION.clear(); location.href = "login.html"; });

  // ---------- Inicio ----------
  (async function init() {
    var s = SESSION.get();
    if (!s) { location.replace("login.html"); return; }
    estId = s.estId; courseId = s.courseId;
    try {
      var lad = await API.lad(estId, courseId);
      renderLad(lad);
      await startChat();
    } catch (er) {
      SESSION.clear();
      location.replace("login.html?error=" + encodeURIComponent(/fetch|network/i.test(er.message) ? "No se pudo conectar con el servidor." : er.message));
    }
  })();
})();