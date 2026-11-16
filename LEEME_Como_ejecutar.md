# Hospital de Computadoras – Registro Digital 2026

## Cómo ejecutarlo en otra computadora
1. Instalar Python 3 (https://www.python.org) — marcar "Add Python to PATH".
2. Abrir una terminal dentro de esta carpeta.
3. Instalar Flask (una sola vez):  `pip install -r requirements.txt`
4. Ejecutar:  `python app.py`
5. Abrir en el navegador:  http://localhost:5000

## Usarlo desde celulares / tablets (misma red WiFi)
1. En la PC que corre la app, averiguar su IP (en Windows: `ipconfig`, buscar "Dirección IPv4", ej. 192.168.1.20).
2. Desde el celular abrir:  http://192.168.1.20:5000
3. Si no conecta, permitir Python en el Firewall de Windows.

## Datos de prueba
`python cargar_datos_prueba.py` agrega 3 fichas de ejemplo.
Para empezar de cero, cerrar la app y borrar `datos/hospital.db`.

## Estados de las computadoras
Solo hay tres: En funcionamiento, Fuera de servicio y En proceso de reparación.
Al abrir la app con una base que tenga estados viejos, se hace sola una copia de seguridad
en `datos/hospital_antes_de_estados_FECHA.db` y se migra: Operativo pasa a En funcionamiento y
No operativo a Fuera de servicio. Las fichas con "Con mantenimiento", "Recuperable" o "Prácticas"
no se adivinan: quedan "A revisar" (con el estado anterior visible en la ficha) hasta que se
elija el estado nuevo desde Editar. No se pierde ningún dato.

## Estructura
- `app.py` – servidor Flask: rutas, base de datos, exportación.
- `templates/` – páginas HTML: `base` (menú lateral), `panel` (inicio con estadísticas), `index` (listado), `form`, `ficha` (informe), `eliminar`, `_iconos` (íconos SVG).
- `static/css/estilo.css` – diseño (paleta futurista: violeta eléctrico, cian, turquesa, lavanda, rosa, grafito, plateado y blanco hielo) y diseño responsivo (celular, tablet, notebook y escritorio; menú lateral deslizable en pantallas chicas).
- `static/img/logo.svg` – logotipo del Hospital de Computadoras.
- `datos/hospital.db` – base SQLite donde quedan guardadas las fichas.
- `cargar_datos_prueba.py` – fichas de ejemplo.

## Direcciones
`/` panel · `/fichas` listado · `/nueva` nueva ficha · `/exportar.csv` · `/respaldo`
