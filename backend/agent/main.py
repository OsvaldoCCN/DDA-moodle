from graph import app
from langchain_core.messages import HumanMessage

if __name__ == "__main__":
    print("=" * 60)
    print("  Tutor Socrático SRL (Arquitectura Modular de Tesis)")
    print("  Escribe 'salir' para terminar.")
    print("=" * 60 + "\n")
    
    ID_ALUMNO_ACTIVO = 1 

    estado_actual = {
        "messages": [],
        "estudiante_id": ID_ALUMNO_ACTIVO,
        "fase_srl_actual": "indefinida",
        "contexto_academico": {},
        "tipo_interaccion": "reactiva",
        "user_message": ""
    }
    
    while True:
        try:
            user_input = input("Estudiante: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nCerrando sesión del tutor.")
            break

        if not user_input:
            continue
            
        if user_input.lower() in ['salir', 'exit', 'quit']:
            print("Cerrando sesión del tutor.")
            break
            
        estado_actual["messages"].append(HumanMessage(content=user_input))
        estado_actual["user_message"] = user_input
        
        print("\n[Pensando y orquestando fase SRL...]")

        nuevo_estado = app.invoke(estado_actual)
        
        respuesta_agente = nuevo_estado["messages"][-1].content
        
        fase = nuevo_estado.get("fase_srl_actual", "indefinida")
        eval_juez = nuevo_estado.get("evaluacion_juez", {}).get("estado", "aprobado")
        
        print(f"\n[Pedagogía SRL: Fase={fase.upper()} | Auditoría Juez={eval_juez.upper()}]")
        print(f"Tutor: {respuesta_agente}\n")
        print("-" * 60)
        
        estado_actual = nuevo_estado