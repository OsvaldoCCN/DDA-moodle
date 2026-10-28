from graph import app
from langchain_core.messages import HumanMessage

if __name__ == "__main__":
    print("🤖 Iniciando Tutor Socrático SRL (Arquitectura Modular)...")
    print("Escribe 'salir' para terminar.\n")
    

    ID_ALUMNO_ACTIVO = 1 
    

    estado_actual = {
        "messages": [],
        "estudiante_id": ID_ALUMNO_ACTIVO
    }
    
    while True:
        user_input = input("Osvaldo: ")
        if user_input.lower() in ['salir', 'exit', 'quit']:
            break
            
        estado_actual["messages"].append(HumanMessage(content=user_input))
        
        print("\n⏳ Pensando...")

        nuevo_estado = app.invoke(estado_actual)
        

        respuesta_agente = nuevo_estado["messages"][-1].content
        print(f"🤖 Tutor: {respuesta_agente}\n")
        print("-" * 50)
        

        estado_actual["messages"] = nuevo_estado["messages"]