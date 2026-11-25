from graph import app
from langchain_core.messages import HumanMessage

if __name__ == "__main__":
    print("=" * 60)
    print("  Tutor Socrático SRL (Arquitectura Modular de Tesis)")
    print("  Escribe 'salir' para terminar.")
    print("=" * 60 + "\n")
    
    ID_ALUMNO_ACTIVO = 3
    ID_CURSO_ACTIVO = 3
    config = {"configurable": {"thread_id": f"est_{ID_ALUMNO_ACTIVO}_curso_{ID_CURSO_ACTIVO}"}}
    
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
            
        estado_entrada = {
            "messages": [HumanMessage(content=user_input)],
            "estudiante_id": ID_ALUMNO_ACTIVO,
            "moodle_courseid": ID_CURSO_ACTIVO,
            "user_message": user_input,
        }
        
        print("\n[Pensando y orquestando fase SRL...]")

        nuevo_estado = app.invoke(estado_entrada, config=config)
        
        respuesta_agente = nuevo_estado["messages"][-1].content
        
        fase = nuevo_estado.get("fase_srl_actual", "indefinida")
        eval_juez = nuevo_estado.get("evaluacion_juez", {}).get("estado", "aprobado")
        
        print(f"\n[Pedagogía SRL: Fase={fase.upper()} | Auditoría Juez={eval_juez.upper()}]")
        print(f"Tutor: {respuesta_agente}\n")
        print("-" * 60)