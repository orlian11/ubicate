import json
import datetime

# Lógica del script que actualiza el JSON según el día de la semana o eventos programados
def generar_eventos():
    hoy = datetime.datetime.now()
    dia_semana = hoy.weekday() # 0: Lunes, 5: Sábado, 6: Domingo
    
    eventos = []
    
    # Ejemplo de automatización basada en días lógicos de alta demanda en Buenos Aires
    if dia_semana in [4, 5, 6]: # Viernes, Sábado, Domingo (Fines de semana con más recitales/movimiento nocturno)
        eventos.append({
            "titulo": "Recital / Evento Masivo en CABA (Movistar Arena / River)",
            "horario": "21:00 hs",
            "salida": "23:30 hs",
            "asistencia": "~15.000 a 60.000 personas",
            "direccion": "Av. Figueroa Alcorta 7597 / Humboldt 450",
            "demanda": "Crítica"
        })
    
    # Evento general de CABA
    eventos.append({
        "titulo": "Flujo General Microcentro / Palermo",
        "horario": "Horario nocturno / Salida gastronómica",
        "salida": "02:00 - 05:00 hs",
        "asistencia": "Alta rotación",
        "direccion": "Palermo Soho y Hollywood, CABA",
        "demanda": "Alta"
    })

    with open("eventos.json", "w", encoding="utf-8") as f:
        json.dump(eventos, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    generar_eventos()