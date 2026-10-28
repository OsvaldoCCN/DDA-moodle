from langchain_openai import ChatOpenAI

from config import (
    OPENROUTER_API_KEY,
    OPENROUTER_URL,
    OPENROUTER_MODEL,
)


llm = ChatOpenAI(
    model=OPENROUTER_MODEL,
    api_key=OPENROUTER_API_KEY,
    base_url=OPENROUTER_URL,
)

SYSTEM_PROMPT = """Eres un tutor virtual socrático de Ingeniería en Informática.
Tu objetivo es fomentar el Aprendizaje Autorregulado (SRL).

REGLAS:
1. NUNCA des la respuesta directa a un problema. Haz preguntas que guíen al estudiante.
2. Si el estudiante habla de sus notas o progreso, DEBES usar tus herramientas.
3. Relaciona su esfuerzo (SCORM) con su desempeño (Cuestionarios) para hacerlo reflexionar.
"""