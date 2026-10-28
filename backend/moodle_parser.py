class MoodleSRLParser:
    """
    Clase encargada de recibir las respuestas JSON crudas de la API de Moodle
    y transformarlas en diccionarios limpios, extrayendo solo la data relevante
    para el modelo SRL (Aprendizaje Autorregulado) y la base de datos del agente.
    """

    @staticmethod
    def limpiar_intentos_cuestionario(raw_data):
        """ Limpia mod_quiz_get_user_attempts """
        intentos_limpios = []
        intentos = raw_data.get('attempts', [])
        
        for intento in intentos:
            # Calcular minutos usados si el intento terminó
            minutos = 0
            if intento.get('timefinish', 0) > 0 and intento.get('timestart', 0) > 0:
                minutos = round((intento['timefinish'] - intento['timestart']) / 60, 2)
                
            intentos_limpios.append({
                "numero_intento": intento.get('attempt'),
                "estado": intento.get('state'),
                "nota": intento.get('sumgrades', 0.0), # Moodle a veces devuelve null si no está calificado
                "minutos_usados": minutos,
                "fecha_inicio": intento.get('timestart'),
                "fecha_fin": intento.get('timefinish')
            })
        return intentos_limpios

    @staticmethod
    def limpiar_tracking_scorm(raw_data):
        """ Limpia mod_scorm_get_scorm_sco_tracks """
        tracks = raw_data.get('data', {}).get('tracks', [])
        datos = {
            "estado": "desconocido",
            "puntaje_raw": None,
            "tiempo_segundos": 0
        }
        
        for track in tracks:
            elemento = track.get('element')
            valor = track.get('value')
            
            if elemento == 'cmi.core.lesson_status' or elemento == 'cmi.completion_status':
                datos["estado"] = valor
            elif elemento == 'cmi.core.score.raw' or elemento == 'cmi.score.raw':
                try:
                    datos["puntaje_raw"] = float(valor)
                except (ValueError, TypeError):
                    pass
            elif elemento == 'cmi.core.session_time' or elemento == 'cmi.session_time':
                # Moodle suele guardar el tiempo en formato HH:MM:SS
                partes = str(valor).split(':')
                if len(partes) == 3:
                    try:
                        segundos = int(partes[0]) * 3600 + int(partes[1]) * 60 + float(partes[2])
                        datos["tiempo_segundos"] += int(segundos)
                    except ValueError:
                        pass
                        
        return datos

    @staticmethod
    def limpiar_status_actividades(raw_data):
        """ Limpia core_completion_get_activities_completion_status """
        # Ideal para la fase de 'Monitoreo' general
        actividades_limpias = []
        statuses = raw_data.get('statuses', [])
        
        for act in statuses:
            actividades_limpias.append({
                "cmid": act.get('cmid'),           # Course Module ID
                "modname": act.get('modname'),     # 'quiz', 'scorm', 'assign', etc.
                "completado": act.get('state') == 1, # 1 es completado, 0 es incompleto
                "fecha_completado": act.get('timecompleted')
            })
        return actividades_limpias

    @staticmethod
    def limpiar_cursos_usuario(raw_data):
        """ Limpia core_enrol_get_users_courses """
        cursos_limpios = []
        for curso in raw_data:
            cursos_limpios.append({
                "curso_id": curso.get('id'),
                "nombre_corto": curso.get('shortname'),
                "nombre_largo": curso.get('fullname'),
                "progreso_porcentaje": curso.get('progress') # Null si no hay completion tracking
            })
        return cursos_limpios

    @staticmethod
    def limpiar_contenido_curso(raw_data):
        """ Limpia core_course_get_contents """
        # Sirve para mapear IDs de módulos (cmid) con sus nombres reales para el prompt del LLM
        modulos = []
        for seccion in raw_data:
            for modulo in seccion.get('modules', []):
                modulos.append({
                    "cmid": modulo.get('id'),
                    "instancia_id": modulo.get('instance'), # ID real del quiz o scorm
                    "tipo": modulo.get('modname'),          # 'quiz', 'assign', etc.
                    "nombre": modulo.get('name'),
                    "seccion": seccion.get('name')
                })
        return modulos

    @staticmethod
    def limpiar_tareas(raw_data):
        """ Limpia mod_assign_get_assignments """
        # Clave para la fase de Planificación SRL (Fechas límite)
        tareas_limpias = []
        for curso in raw_data.get('courses', []):
            for tarea in curso.get('assignments', []):
                tareas_limpias.append({
                    "tarea_id": tarea.get('id'),
                    "curso_id": tarea.get('course'),
                    "nombre": tarea.get('name'),
                    "fecha_limite": tarea.get('duedate'),
                    "fecha_apertura": tarea.get('allowsubmissionsfromdate')
                })
        return tareas_limpias

    @staticmethod
    def limpiar_quizzes(raw_data):
        """ Limpia mod_quiz_get_quizzes_by_courses """
        quizzes = []
        for quiz in raw_data.get('quizzes', []):
            quizzes.append({
                "quiz_id": quiz.get('id'),
                "curso_id": quiz.get('course'),
                "nombre": quiz.get('name'),
                "fecha_cierre": quiz.get('timeclose')
            })
        return quizzes

    @staticmethod
    def limpiar_scorms(raw_data):
        """ Limpia mod_scorm_get_scorms_by_courses """
        scorms = []
        for scorm in raw_data.get('scorms', []):
            scorms.append({
                "scorm_id": scorm.get('id'),
                "curso_id": scorm.get('course'),
                "nombre": scorm.get('name')
            })
        return scorms