import json
import datetime

def generar_eventos():
    # Obtenemos la fecha de hoy y de mañana en formato legible (DD/MM/YYYY)
    hoy = datetime.datetime.now()
    manana = hoy + datetime.timedelta(days=1)
    
    str_hoy = hoy.strftime("%d/%m/%Y")
    str_manana = manana.strftime("%d/%m/%Y")

    eventos = [
        {
            "categoria": "clima",
            "titulo": "Alerta de Tránsito y Lluvia / Alta Demanda",
            "fecha": str_hoy,
            "horario": "Pico nocturno",
            "salida": "Variable",
            "asistencia": "Multiplicador alto de viajes",
            "direccion": "Microcentro y Zonas Residenciales CABA",
            "demanda": "Muy Alta"
        },
        {
            "categoria": "deportes",
            "titulo": "Torneo Liga Profesional: River Plate vs. Boca Juniors (Superclásico)",
            "fecha": str_manana, # Asignado para mañana con fecha real
            "horario": "17:00 - 19:30 hs",
            "salida": "19:30 - 21:00 hs",
            "asistencia": "~80.000 personas",
            "direccion": "Av. Figueroa Alcorta 7597, Núñez, CABA (Mâs Monumental)",
            "demanda": "Crítica"
        },
        {
            "categoria": "deportes",
            "titulo": "Copa Argentina: Racing Club vs. Independiente",
            "fecha": str_hoy,
            "horario": "21:00 - 23:00 hs",
            "salida": "23:00 - 00:30 hs",
            "asistencia": "~50.000 personas",
            "direccion": "Av. Mitre 4700, Avellaneda (Estadio Libertadores de América)",
            "demanda": "Crítica"
        },
        {
            "categoria": "espectaculos",
            "titulo": "Concierto en Vivo: Coldplay - Gira Mundial",
            "fecha": str_manana,
            "horario": "21:00 hs",
            "salida": "23:00 - 00:30 hs",
            "asistencia": "~15.000 personas",
            "direccion": "Humboldt 450, Villa Crespo, CABA (Movistar Arena)",
            "demanda": "Alta"
        },
        {
            "categoria": "espectaculos",
            "titulo": "Festival Musical: Lali Espósito en Concierto",
            "fecha": str_hoy,
            "horario": "20:00 hs en adelante",
            "salida": "Madrugada",
            "asistencia": "Alta afluencia de público",
            "direccion": "Av. Del Libertador 4101, Palermo, CABA (Hipódromo de Palermo)",
            "demanda": "Alta"
        }
    ]

    with open("eventos.json", "w", encoding="utf-8") as f:
        json.dump(eventos, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    generar_eventos()
