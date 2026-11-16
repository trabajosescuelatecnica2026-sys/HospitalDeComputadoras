"""
Hospital de Computadoras - Registro Digital de Diagnóstico
Expo Técnica 2026 - Escuela Técnica Dr. J. R. Vidal

Este archivo es el "motor" de la aplicación (Python + Flask).
Cada función con @app.route es una "ruta": una dirección web que
el navegador puede visitar y que Python responde.
"""

import csv
import io
import os
import sqlite3
from datetime import date, datetime, timedelta

from flask import (Flask, Response, abort, flash, g, redirect,
                   render_template, request, send_file, url_for)

app = Flask(__name__)
# Flask usa esta clave para los mensajes "flash" (avisos de una sola vez).
app.secret_key = "hospital-de-computadoras-2026"

# ----------------------------------------------------------------------
# Configuración
# ----------------------------------------------------------------------
CARPETA = os.path.dirname(os.path.abspath(__file__))
RUTA_DB = os.path.join(CARPETA, "datos", "hospital.db")

# Opciones de la lista desplegable de "Estado final".
ESTADOS_FINALES = ["En funcionamiento", "Fuera de servicio", "En proceso de reparación"]

# Migración de los estados antiguos (solo los que tienen un equivalente claro).
# Los demás ("Con mantenimiento", "Recuperable", "Prácticas") no se adivinan:
# quedan "Sin definir", marcados "A revisar", y el valor original se guarda en
# la columna estado_anterior.
EQUIVALENCIAS_ESTADOS = {"Operativo": "En funcionamiento",
                         "No operativo": "Fuera de servicio"}

# Campos de texto de la planilla: (nombre en la base, etiqueta visible, ¿texto largo?)
CAMPOS_TEXTO = [
    ("paciente",     "Paciente",                    False),
    ("marca_modelo", "Marca / Modelo",              False),
    ("sintoma",      "Síntoma",                     True),
    ("estado_inicial", "Estado inicial",            True),
    ("estudios",     "Estudios realizados",         True),
    ("resultados",   "Resultados",                  True),
    ("diagnostico",  "Diagnóstico",                 True),
    ("tratamiento",  "Tratamiento / intervención",  True),
    ("componentes",  "Componentes reemplazados",    False),
    ("prueba_final", "Prueba final",                True),
]

# Todos los campos que se guardan al enviar el formulario (sin el código ni el id).
CAMPOS_FORM = [c[0] for c in CAMPOS_TEXTO] + [
    "estado_final", "fecha_ingreso", "fecha_egreso", "tecnico"]


# ----------------------------------------------------------------------
# Base de datos (SQLite: un único archivo, sin instalar nada)
# ----------------------------------------------------------------------
def get_db():
    """Abre la conexión a la base una sola vez por pedido."""
    if "db" not in g:
        g.db = sqlite3.connect(RUTA_DB)
        g.db.row_factory = sqlite3.Row  # permite usar fila["paciente"]
    return g.db


@app.teardown_appcontext
def cerrar_db(error=None):
    """Cierra la conexión cuando termina el pedido."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Crea la tabla si todavía no existe."""
    os.makedirs(os.path.dirname(RUTA_DB), exist_ok=True)
    con = sqlite3.connect(RUTA_DB)
    con.execute("""
        CREATE TABLE IF NOT EXISTS fichas (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo        TEXT,
            paciente      TEXT NOT NULL,
            marca_modelo  TEXT,
            sintoma       TEXT NOT NULL,
            estado_inicial TEXT,
            estudios      TEXT,
            resultados    TEXT,
            diagnostico   TEXT,
            tratamiento   TEXT,
            componentes   TEXT,
            prueba_final  TEXT,
            estado_final  TEXT,
            fecha_ingreso TEXT,
            fecha_egreso  TEXT,
            tecnico       TEXT,
            estado_anterior TEXT
        )
    """)
    con.commit()
    con.close()
    migrar_estados()


def migrar_estados():
    """Pasa los estados antiguos a los tres estados nuevos, sin perder datos.

    1. Si hay fichas con estados antiguos, primero guarda una copia de la base
       en la carpeta datos/ (hospital_antes_de_estados_FECHA.db).
    2. Agrega la columna estado_anterior si todavía no existe.
    3. Cambia solo los estados con equivalente claro; en los demás conserva
       el valor original en estado_anterior y deja el estado como "Sin definir"
       para que se revise a mano (se ve como "A revisar").
    Es seguro ejecutarla muchas veces: si no hay nada para migrar, no hace nada.
    """
    con = sqlite3.connect(RUTA_DB)
    marcas = ", ".join("?" for _ in ESTADOS_FINALES)
    antiguas = con.execute(
        f"SELECT id, estado_final FROM fichas WHERE estado_final IS NOT NULL "
        f"AND estado_final != '' AND estado_final NOT IN ({marcas})",
        ESTADOS_FINALES).fetchall()
    if antiguas:
        copia = os.path.join(os.path.dirname(RUTA_DB),
                             f"hospital_antes_de_estados_{datetime.now():%Y%m%d_%H%M%S}.db")
        origen = sqlite3.connect(RUTA_DB)
        destino = sqlite3.connect(copia)
        origen.backup(destino)  # copia consistente de toda la base
        destino.close()
        origen.close()
    columnas = [c[1] for c in con.execute("PRAGMA table_info(fichas)")]
    if "estado_anterior" not in columnas:
        con.execute("ALTER TABLE fichas ADD COLUMN estado_anterior TEXT")
    for ficha_id, viejo in antiguas:
        nuevo = EQUIVALENCIAS_ESTADOS.get(viejo)
        if nuevo:
            con.execute("UPDATE fichas SET estado_final = ?, estado_anterior = ? WHERE id = ?",
                        (nuevo, viejo, ficha_id))
        else:
            con.execute("UPDATE fichas SET estado_final = '', estado_anterior = ? WHERE id = ?",
                        (viejo, ficha_id))
    con.commit()
    con.close()


# ----------------------------------------------------------------------
# Funciones auxiliares
# ----------------------------------------------------------------------
def leer_formulario():
    """Toma los datos que llegaron del formulario y les saca espacios sobrantes."""
    return {campo: request.form.get(campo, "").strip() for campo in CAMPOS_FORM}


def validar(datos):
    """Validación básica: Paciente y Síntoma son obligatorios."""
    errores = []
    if not datos["paciente"]:
        errores.append("El campo Paciente no puede quedar vacío.")
    if not datos["sintoma"]:
        errores.append("El campo Síntoma no puede quedar vacío.")
    if datos["estado_final"] and datos["estado_final"] not in ESTADOS_FINALES:
        errores.append("El Estado final elegido no es válido.")
    return errores


def buscar_ficha(ficha_id):
    """Trae una ficha por su id; si no existe, muestra error 404."""
    ficha = get_db().execute("SELECT * FROM fichas WHERE id = ?", (ficha_id,)).fetchone()
    if ficha is None:
        abort(404)
    return ficha


@app.template_filter("fecha")
def formatear_fecha(valor):
    """Muestra '2026-11-13T10:30' como '2026-11-13 10:30'."""
    return valor.replace("T", " ") if valor else "—"


CLASES_ESTADO = {"En funcionamiento": "fun", "Fuera de servicio": "fue",
                 "En proceso de reparación": "rep"}


@app.template_filter("ec")
def clase_estado(nombre):
    """Devuelve la clase de color (CSS) de cada estado final."""
    return CLASES_ESTADO.get(nombre, "sin")


def calcular_resumen(db):
    """Cuenta fichas totales y por estado (lo usan el panel y el listado)."""
    resumen = {"total": db.execute("SELECT COUNT(*) FROM fichas").fetchone()[0]}
    for e in ESTADOS_FINALES:
        resumen[e] = db.execute(
            "SELECT COUNT(*) FROM fichas WHERE estado_final = ?", (e,)).fetchone()[0]
    resumen["Sin definir"] = db.execute(
        "SELECT COUNT(*) FROM fichas WHERE estado_final IS NULL OR estado_final = ''"
    ).fetchone()[0]
    return resumen


# ----------------------------------------------------------------------
# Rutas
# ----------------------------------------------------------------------
@app.route("/")
def panel():
    """Panel principal: estadísticas, gráficos y últimos registros."""
    db = get_db()
    resumen = calcular_resumen(db)
    total = resumen["total"]
    ultimos = db.execute("SELECT * FROM fichas ORDER BY id DESC LIMIT 5").fetchall()

    # Ingresos de los últimos 7 días (para el gráfico de barras)
    dias = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
    por_dia = []
    for i in range(6, -1, -1):
        d = date.today() - timedelta(days=i)
        n = db.execute("SELECT COUNT(*) FROM fichas WHERE fecha_ingreso LIKE ?",
                       (f"{d.isoformat()}%",)).fetchone()[0]
        por_dia.append({"dia": dias[d.weekday()], "n": n})
    maximo = max([x["n"] for x in por_dia] + [1])
    for x in por_dia:
        x["alto"] = round(x["n"] * 100 / maximo)

    # Segmentos del gráfico circular (cada uno: largo y desplazamiento en %)
    segmentos, acumulado = [], 0
    for nombre in ESTADOS_FINALES + ["Sin definir"]:
        pct = resumen[nombre] * 100 / total if total else 0
        segmentos.append({"nombre": nombre, "cantidad": resumen[nombre],
                          "pct": round(pct, 2), "offset": round(-acumulado, 2)})
        acumulado += pct

    tasa = round(resumen["En funcionamiento"] * 100 / total) if total else 0
    return render_template("panel.html", resumen=resumen, ultimos=ultimos,
                           por_dia=por_dia, segmentos=segmentos, tasa=tasa)


@app.route("/fichas")
def listado():
    """Lista de fichas con buscador, filtros y resumen."""
    q = request.args.get("q", "").strip()
    estado = request.args.get("estado", "").strip()
    marca = request.args.get("marca", "").strip()
    fecha = request.args.get("fecha", "").strip()

    # Armamos la consulta SQL de a pedazos. Los "?" evitan inyección SQL.
    sql = "SELECT * FROM fichas WHERE 1=1"
    parametros = []
    if q:
        sql += " AND (codigo LIKE ? OR paciente LIKE ? OR sintoma LIKE ? OR diagnostico LIKE ?)"
        parametros += [f"%{q}%"] * 4
    if estado == "sin_definir":
        sql += " AND (estado_final IS NULL OR estado_final = '')"
    elif estado:
        sql += " AND estado_final = ?"
        parametros.append(estado)
    if marca:
        sql += " AND marca_modelo LIKE ?"
        parametros.append(f"%{marca}%")
    if fecha:
        sql += " AND fecha_ingreso LIKE ?"
        parametros.append(f"{fecha}%")
    sql += " ORDER BY id DESC"

    db = get_db()
    fichas = db.execute(sql, parametros).fetchall()

    resumen = calcular_resumen(db)  # sobre TODAS las fichas, no solo las filtradas

    return render_template("index.html", fichas=fichas, resumen=resumen,
                           estados=ESTADOS_FINALES,
                           filtros={"q": q, "estado": estado, "marca": marca, "fecha": fecha})


@app.route("/nueva", methods=["GET", "POST"])
def nueva():
    """Formulario para cargar una ficha nueva."""
    if request.method == "POST":
        datos = leer_formulario()
        errores = validar(datos)
        if errores:
            # Volvemos a mostrar el formulario conservando lo que escribieron.
            return render_template("form.html", datos=datos, errores=errores,
                                   campos=CAMPOS_TEXTO, estados=ESTADOS_FINALES,
                                   modo="nueva")
        db = get_db()
        columnas = ", ".join(CAMPOS_FORM)
        marcas = ", ".join("?" for _ in CAMPOS_FORM)
        cursor = db.execute(f"INSERT INTO fichas ({columnas}) VALUES ({marcas})",
                            [datos[c] for c in CAMPOS_FORM])
        nuevo_id = cursor.lastrowid
        # El código se genera solo a partir del id: PC-001, PC-002, ...
        db.execute("UPDATE fichas SET codigo = ? WHERE id = ?",
                   (f"PC-{nuevo_id:03d}", nuevo_id))
        db.commit()
        flash(f"Ficha PC-{nuevo_id:03d} guardada correctamente.")
        return redirect(url_for("ver", ficha_id=nuevo_id))

    # GET: formulario vacío, con la fecha de ingreso de este momento.
    datos = {c: "" for c in CAMPOS_FORM}
    datos["fecha_ingreso"] = datetime.now().strftime("%Y-%m-%dT%H:%M")
    return render_template("form.html", datos=datos, errores=[],
                           campos=CAMPOS_TEXTO, estados=ESTADOS_FINALES, modo="nueva")


@app.route("/ficha/<int:ficha_id>")
def ver(ficha_id):
    """Muestra una ficha completa (también sirve para imprimirla con Ctrl+P)."""
    return render_template("ficha.html", f=buscar_ficha(ficha_id), campos=CAMPOS_TEXTO)


@app.route("/ficha/<int:ficha_id>/editar", methods=["GET", "POST"])
def editar(ficha_id):
    """Editar una ficha para ir completando diagnóstico, tratamiento y estado final."""
    ficha = buscar_ficha(ficha_id)
    if request.method == "POST":
        datos = leer_formulario()
        errores = validar(datos)
        if errores:
            return render_template("form.html", datos=datos, errores=errores,
                                   campos=CAMPOS_TEXTO, estados=ESTADOS_FINALES,
                                   modo="editar", ficha=ficha)
        asignaciones = ", ".join(f"{c} = ?" for c in CAMPOS_FORM)
        db = get_db()
        db.execute(f"UPDATE fichas SET {asignaciones} WHERE id = ?",
                   [datos[c] for c in CAMPOS_FORM] + [ficha_id])
        db.commit()
        flash("Cambios guardados.")
        return redirect(url_for("ver", ficha_id=ficha_id))

    datos = {c: ficha[c] or "" for c in CAMPOS_FORM}
    return render_template("form.html", datos=datos, errores=[], campos=CAMPOS_TEXTO,
                           estados=ESTADOS_FINALES, modo="editar", ficha=ficha)


@app.route("/ficha/<int:ficha_id>/eliminar", methods=["GET", "POST"])
def eliminar(ficha_id):
    """Pide confirmación (GET) y recién borra cuando se confirma (POST)."""
    ficha = buscar_ficha(ficha_id)
    if request.method == "POST":
        db = get_db()
        db.execute("DELETE FROM fichas WHERE id = ?", (ficha_id,))
        db.commit()
        flash(f"Ficha {ficha['codigo']} eliminada.")
        return redirect(url_for("listado"))
    return render_template("eliminar.html", f=ficha)


@app.route("/exportar.csv")
def exportar():
    """Descarga todos los registros en CSV (se abre con Excel)."""
    filas = get_db().execute("SELECT * FROM fichas ORDER BY id").fetchall()
    salida = io.StringIO()
    # Punto y coma: Excel en español lo separa en columnas sin configurar nada.
    escritor = csv.writer(salida, delimiter=";")
    encabezados = ["PC"] + [c[1] for c in CAMPOS_TEXTO] + [
        "Estado final", "Fecha de ingreso", "Fecha de egreso", "Técnico/a"]
    escritor.writerow(encabezados)
    for f in filas:
        escritor.writerow(
            [f["codigo"]] + [f[c[0]] or "" for c in CAMPOS_TEXTO] + [
                f["estado_final"] or "", formatear_fecha(f["fecha_ingreso"]).replace("—", ""),
                formatear_fecha(f["fecha_egreso"]).replace("—", ""), f["tecnico"] or ""])
    # "\ufeff" (BOM) hace que Excel respete tildes y eñes.
    contenido = "\ufeff" + salida.getvalue()
    nombre = f"hospital_pcs_{datetime.now():%Y%m%d_%H%M}.csv"
    return Response(contenido, mimetype="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f"attachment; filename={nombre}"})


@app.route("/respaldo")
def respaldo():
    """Descarga una copia de seguridad de la base de datos completa."""
    nombre = f"respaldo_hospital_{datetime.now():%Y%m%d_%H%M}.db"
    return send_file(RUTA_DB, as_attachment=True, download_name=nombre)


@app.errorhandler(404)
def no_encontrado(error):
    return render_template("404.html"), 404


# ----------------------------------------------------------------------
# Arranque
# ----------------------------------------------------------------------
init_db()

if __name__ == "__main__":
    # host="0.0.0.0" permite entrar desde otros dispositivos de la misma red
    # usando http://IP-DE-LA-PC:5000
    app.run(host="0.0.0.0", port=5000, debug=False)
