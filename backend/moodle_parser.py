class MoodleSRLParser:
    
    @staticmethod
    def limpiar_cursos(raw_courses):
        """
        Recibe el JSON crudo de core_enrol_get_users_courses y extrae 
        solo lo necesario para el dashboard SRL y el contexto del bot.
        """
        # Si Moodle devuelve un error o viene vacío, devolvemos una lista vacía
        if not raw_courses or (isinstance(raw_courses, dict) and "exception" in raw_courses):
            return []
            
        cursos_limpios = []
        for course in raw_courses:
            cursos_limpios.append({
                "id_curso": course.get("id"),
                "nombre": course.get("fullname"),
                "progreso": course.get("progress"),
                "completado": course.get("completed")
            })
            
        return cursos_limpios


    @staticmethod
    def limpiar_contenidos(raw_contents):
        """
        Extrae la jerarquía del curso (secciones y actividades) 
        para darle contexto al agente LangGraph sobre qué debe estudiar el alumno.
        """
        if not isinstance(raw_contents, list):
            return []
            
        contenidos_limpios = []
        for seccion in raw_contents:
            # Filtramos secciones que no tienen actividades para reducir ruido
            if not seccion.get("modules"):
                continue
                
            actividades = []
            for modulo in seccion.get("modules", []):
                actividades.append({
                    "id_modulo": modulo.get("id"), # Vital para cruzarlo con notas/progreso luego
                    "nombre": modulo.get("name"),
                    "tipo": modulo.get("modname")  # Sirve para saber si es foro, tarea, scorm, etc.
                })
                
            contenidos_limpios.append({
                "seccion": seccion.get("name"),
                "actividades": actividades
            })
            
        return contenidos_limpios

    @staticmethod
    def limpiar_tareas(raw_assignments):
        """
        Extrae las tareas y fechas límite (duedate) para la fase de Planificación del SRL.
        """
        if not isinstance(raw_assignments, dict) or "courses" not in raw_assignments:
            return []
            
        tareas_limpias = []
        for course in raw_assignments["courses"]:
            for assignment in course.get("assignments", []):
                tareas_limpias.append({
                    "id_curso": course.get("id"),
                    "id_tarea": assignment.get("id"),
                    "nombre_tarea": assignment.get("name"),
                    "fecha_limite": assignment.get("duedate") # Esto viene en timestamp (ej: 1790895600)
                })
                
        return tareas_limpias

    
    @staticmethod
    def limpiar_intentos_cuestionario(raw_attempts):
        """
        Extrae los intentos de un cuestionario para evaluar el rendimiento y la reflexión.
        """
        if not isinstance(raw_attempts, dict) or "attempts" not in raw_attempts:
            return []
            
        intentos_limpios = []
        for intento in raw_attempts["attempts"]:
            # Solución: Usamos 'or' para que si timecheckstate es None, salte a timestart
            tiempo_inicio = intento.get("timecheckstate") or intento.get("timestart")
            tiempo_fin = intento.get("timefinish")
            
            minutos_usados = 0
            if tiempo_fin and tiempo_inicio:
                minutos_usados = round((tiempo_fin - tiempo_inicio) / 60, 2)
            
            intentos_limpios.append({
                "id_cuestionario": intento.get("quiz"),
                "numero_intento": intento.get("attempt"),
                "estado": intento.get("state"), # Puede ser 'inprogress', 'finished'
                "nota": intento.get("sumgrades"),
                "minutos_usados": minutos_usados
            })
            
        return intentos_limpios
    

    @staticmethod
    def limpiar_tracking_scorm(raw_tracks):
        """
        Extrae las métricas granulares del SCORM (tiempo y estado) para evaluar el Monitoreo del SRL.
        """
        if not isinstance(raw_tracks, dict) or "data" not in raw_tracks or not raw_tracks["data"]["tracks"]:
            return {}
            
        # El SCORM devuelve una lista de pares "elemento -> valor". Vamos a convertirlos en un diccionario simple.
        scorm_data = {
            "estado": "desconocido",
            "tiempo_segundos": 0,
            "puntaje_raw": None
        }
        
        for track in raw_tracks["data"]["tracks"]:
            elemento = track.get("element")
            valor = track.get("value")
            
            if elemento == "cmi.core.lesson_status":
                scorm_data["estado"] = valor  # ej: 'completed', 'incomplete', 'passed', 'failed'
            elif elemento == "cmi.core.session_time":
                scorm_data["tiempo_str"] = valor # SCORM lo guarda en formato extraño, lo guardamos crudo por si acaso
            elif elemento == "cmi.core.score.raw":
                scorm_data["puntaje_raw"] = valor
                
        return scorm_data