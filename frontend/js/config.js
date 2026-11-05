// Configuración del frontend.
// USE_MOCK = true  -> funciona sin backend, con datos de ejemplo (útil para la demo).
// USE_MOCK = false -> llama a la API FastAPI (backend/agent/api.py).
window.CONFIG = {
  USE_MOCK: false,
  API_URL: ""   // vacío = misma dirección desde donde se abrió la página (recomendado en el VPS)
};
