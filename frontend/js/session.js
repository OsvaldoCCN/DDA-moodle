// Sesión mínima del estudiante, compartida entre login.html y panel.html.
// Se guarda en sessionStorage: se borra al cerrar la pestaña.
window.SESSION = {
  get: function () {
    try {
      var s = JSON.parse(sessionStorage.getItem("srl_session") || "null");
      return s && s.estId && s.courseId ? s : null;
    } catch (e) { return null; }
  },
  set: function (estId, courseId) {
    try { sessionStorage.setItem("srl_session", JSON.stringify({ estId: estId, courseId: courseId })); } catch (e) {}
  },
  clear: function () {
    try { sessionStorage.removeItem("srl_session"); } catch (e) {}
  }
};
