"""
Carga algunas fichas de ejemplo para probar la aplicación.
Uso:  python cargar_datos_prueba.py
"""
import sqlite3
from app import init_db, RUTA_DB

EJEMPLOS = [
    ("Torre gamer del aula 3", "Genérica / Ryzen 5", "No enciende.",
     "Fuente sin respuesta, sin luces.", "Prueba de fuente con tester.",
     "La fuente no entrega tensión.", "Fuente de alimentación dañada.",
     "Se reemplazó la fuente.", "Fuente 500 W", "Encendió y pasó 30 min de prueba.",
     "En funcionamiento", "2026-11-13T09:15", "2026-11-13T10:40", "Equipo A"),
    ("Notebook de biblioteca", "Lenovo ThinkPad", "Muy lenta al iniciar.",
     "Windows tarda 8 minutos en cargar.", "Revisión de disco y memoria.",
     "Disco con sectores dañados.", "Disco rígido en mal estado.",
     "Clonado y cambio por SSD.", "SSD 240 GB", "Inicia en 25 segundos.",
     "En proceso de reparación", "2026-11-13T09:45", "", "Equipo B"),
    ("PC de oficina", "HP Compaq", "Pantalla negra, pitidos.",
     "Emite pitidos repetidos al encender.", "Prueba de módulos de RAM.",
     "Un módulo no es detectado.", "Falla de RAM.", "", "",
     "", "", "2026-11-13T10:05", "", "Equipo A"),
]

init_db()
con = sqlite3.connect(RUTA_DB)
for e in EJEMPLOS:
    cur = con.execute(
        """INSERT INTO fichas (paciente, marca_modelo, sintoma, estado_inicial, estudios,
           resultados, diagnostico, tratamiento, componentes, prueba_final, estado_final,
           fecha_ingreso, fecha_egreso, tecnico) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", e)
    con.execute("UPDATE fichas SET codigo = ? WHERE id = ?",
                (f"PC-{cur.lastrowid:03d}", cur.lastrowid))
con.commit()
con.close()
print("Listo: se cargaron", len(EJEMPLOS), "fichas de prueba.")
