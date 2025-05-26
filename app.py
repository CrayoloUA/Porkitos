from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import psycopg2
import psycopg2.extras
import re
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = 'julian2006'

# Configuración de la base de datos PostgreSQL en Render
DB_CONFIG = {
    'cuadrecaja': {
        'host': 'dpg-d0h5rlk9c44c73822agg-a.oregon-postgres.render.com',
        'user': 'cuadrecaja_user',
        'password': 'QqzAEGN7W8RI7GImG51dwasWfmFFo1nL',
        'dbname': 'cuadrecaja'
    },
    'villa_colombia': {
        'host': 'dpg-d0h5rlk9c44c73822agg-a.oregon-postgres.render.com',
        'user': 'cuadrecaja_user',
        'password': 'QqzAEGN7W8RI7GImG51dwasWfmFFo1nL',
        'dbname': 'villa_colombia'
    }
}

def get_db_connection(db_name):
    try:
        conn = psycopg2.connect(
            host=DB_CONFIG[db_name]['host'],
            user=DB_CONFIG[db_name]['user'],
            password=DB_CONFIG[db_name]['password'],
            dbname=DB_CONFIG[db_name]['dbname']
        )
        return conn
    except psycopg2.Error as err:
        print(f"Error de conexión: {err}")
        return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/guadalupe')
def guadalupe():
    conn = psycopg2.connect(database="cuadrecaja", user="postgres", password="admin", host="localhost", port="5432")
    cur = conn.cursor()

    # Total efectivo
    cur.execute("SELECT efectivo_sede FROM cierredia ORDER BY id DESC LIMIT 1")
    total_efectivo = cur.fetchone()[0]

    # Ventas Didi (Crédito + Efectivo)
    cur.execute("SELECT COALESCE(SUM(didi_credito + didi_efectivo), 0) FROM ventadidi")
    total_didi = cur.fetchone()[0]

    # Ventas QR
    cur.execute("SELECT COALESCE(SUM(codigo_qr), 0) FROM discriminacionventadia")
    total_qr = cur.fetchone()[0]

    # Egresos del día
    cur.execute("SELECT COALESCE(SUM(valor), 0) FROM egresosdeldia")
    total_egresos = cur.fetchone()[0]

    # Venta total
    cur.execute("SELECT COALESCE(SUM(total), 0) FROM discriminacionventadia")
    venta_total = cur.fetchone()[0]

    # Efectivo restante
    efectivo_restante = total_efectivo - total_egresos + total_didi + total_qr

    conn.close()

    return render_template("guadalupe.html",
                           total_efectivo=total_efectivo,
                           total_didi=total_didi,
                           total_qr=total_qr,
                           total_egresos=total_egresos,
                           venta_total=venta_total,
                           efectivo_restante=efectivo_restante,
                           ventas_momento=venta_total)


@app.route('/seleccionar_edicion', methods=['GET', 'POST'])
@login_required
def seleccionar_edicion():
    if request.method == 'POST':
        local = request.form.get('local')
        return redirect(url_for('editar_registros', local=local))
    return render_template('seleccionar_edicion.html')


@app.route('/editar_registros', methods=['GET', 'POST'])
@login_required
def editar_registros():
    local = request.args.get('local', 'Guadalupe')
    conn = get_db_connection('cuadrecaja' if local == 'Guadalupe' else 'villa_colombia')
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
    tablas = [row['table_name'] for row in cursor.fetchall()]
    tabla_seleccionada = request.form.get('tabla')
    registros = []

    if tabla_seleccionada:
        try:
            cursor.execute(f"SELECT * FROM {tabla_seleccionada}")
            registros = cursor.fetchall()
        except:
            flash(f"No se pudo cargar la tabla {tabla_seleccionada}")

    cursor.close()
    conn.close()

    return render_template('editar_registros.html',
                           tablas=tablas,
                           registros=registros,
                           tabla_seleccionada=tabla_seleccionada,
                           local=local)


@app.route('/editar/<string:local>/<string:tabla>/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_registro(local, tabla, id):
    conn = get_db_connection('cuadrecaja' if local == 'Guadalupe' else 'villa_colombia')
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if request.method == 'POST':
        nuevos_valores = {k: v for k, v in request.form.items()}
        sets = ', '.join([f"{k} = %s" for k in nuevos_valores.keys()])
        valores = list(nuevos_valores.values()) + [id]
        try:
            cursor.execute(f"UPDATE {tabla} SET {sets} WHERE id = %s", valores)
            conn.commit()
            flash("Registro actualizado correctamente.")
            return redirect(url_for('fronted' if local == 'Guadalupe' else 'fronted_villa_colombia'))
        except Exception as e:
            flash(f"Error al actualizar: {e}")
    else:
        cursor.execute(f"SELECT * FROM {tabla} WHERE id = %s", (id,))
        registro = cursor.fetchone()
        columnas = [desc[0] for desc in cursor.description]

    cursor.close()
    conn.close()
    return render_template('editar_registro.html', registro=registro, columnas=columnas, tabla=tabla, local=local)


@app.route('/eliminar/<string:local>/<string:tabla>/<int:id>', methods=['POST'])
@login_required
def eliminar_registro(local, tabla, id):
    conn = get_db_connection('cuadrecaja' if local == 'Guadalupe' else 'villa_colombia')
    cursor = conn.cursor()
    try:
        cursor.execute(f"DELETE FROM {tabla} WHERE id = %s", (id,))
        conn.commit()
        flash("Registro eliminado correctamente.")
    except Exception as e:
        flash(f"Error al eliminar: {e}")
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('fronted' if local == 'Guadalupe' else 'fronted_villa_colombia'))



@app.route('/landing')
def landing():
    return render_template('landing.html')

@app.route('/')
def home_redirect():
    return redirect(url_for('landing'))


@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    usuario_correcto = 'root'
    clave_correcta_hash = generate_password_hash('julian2006')
    usuario_lacafetera = 'Porkitos'
    clave_lacafetera_hash = generate_password_hash('Porkitos1234')

    if request.method == 'POST':
        usuario = request.form['usuario']
        clave = request.form['clave']

        if usuario == usuario_correcto and check_password_hash(clave_correcta_hash, clave):
            session['logged_in'] = True
            session['username'] = usuario
            return redirect('http://localhost/phpmyadmin')
        elif usuario == usuario_lacafetera and check_password_hash(clave_lacafetera_hash, clave):
            session['logged_in'] = True
            session['username'] = usuario
            return redirect(url_for('elegir_cuadre'))
        else:
            error = "Credenciales incorrectas, por favor intente nuevamente."

    return render_template('login.html', error=error)

@app.route('/elegir_cuadre', methods=['GET', 'POST'])
@login_required
def elegir_cuadre():
    if request.method == 'POST':
        local_seleccionado = request.form['local']
        if local_seleccionado == "Guadalupe":
            return redirect(url_for('fronted'))
        elif local_seleccionado == "Villa Colombia":
            return redirect(url_for('fronted_villa_colombia'))
    return render_template('elegir_cuadre.html')

@app.route('/fronted', methods=['GET', 'POST'])
@login_required
def fronted():
    conn = get_db_connection('cuadrecaja')
    if not conn:
        return "Error de conexión a la base de datos", 500
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
    tables = [row['table_name'] for row in cursor.fetchall()]
    registros = []
    tabla_seleccionada = None

    if request.method == 'POST':
        tabla = request.form['tabla']
        tabla_seleccionada = tabla
        campos = {k.split('[')[1].replace(']', ''): v for k, v in request.form.items() if k.startswith('campos[')}
        if 'efectivo' in campos: del campos['efectivo']
        if 'id' in campos: del campos['id']

        if tabla and campos:
            try:
                nombres_campos = ", ".join(campos.keys())
                valores_placeholder = ", ".join(["%s"] * len(campos))
                valores_campos = list(campos.values())
                query = f"INSERT INTO {tabla} ({nombres_campos}) VALUES ({valores_placeholder})"
                cursor.execute(query, valores_campos)
                conn.commit()
                flash("Datos insertados correctamente.")
            except psycopg2.Error as err:
                flash(f"Ocurrió un error al insertar los datos: {err}")
        # Mostrar registros después de insertar
        try:
            cursor.execute(f"SELECT * FROM {tabla}")
            registros = cursor.fetchall()
        except:
            registros = []

    cursor.close()
    conn.close()
    return render_template('fronted.html', tables=tables, registros=registros, tabla_seleccionada=tabla_seleccionada, local="Guadalupe")

... 

@app.route('/fronted_villa_colombia', methods=['GET', 'POST'])
@login_required
def fronted_villa_colombia():
    conn = get_db_connection('villa_colombia')
    if not conn:
        return "Error de conexión a la base de datos", 500
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
    tables = [row['table_name'] for row in cursor.fetchall()]

    if request.method == 'POST':
        tabla = request.form['tabla']
        campos = {k.split('[')[1].replace(']', ''): v for k, v in request.form.items() if k.startswith('campos[')}
        if 'efectivo' in campos: del campos['efectivo']
        if 'id' in campos: del campos['id']

        if tabla and campos:
            try:
                nombres_campos = ", ".join(campos.keys())
                valores_placeholder = ", ".join(["%s"] * len(campos))
                valores_campos = list(campos.values())
                query = f"INSERT INTO {tabla} ({nombres_campos}) VALUES ({valores_placeholder})"
                cursor.execute(query, valores_campos)
                conn.commit()
                flash("Datos insertados correctamente.")
                return redirect(url_for('fronted_villa_colombia'))
            except psycopg2.Error as err:
                print(f"Error al insertar datos: {err}")
                flash(f"Ocurrió un error al insertar los datos: {err}")

    cursor.close()
    conn.close()
    return render_template('fronted_villa_colombia.html', tables=tables)

...

@app.route('/obtener_campos')
def obtener_campos():
    tabla = request.args.get('tabla')
    if not tabla or not re.match(r'^[a-zA-Z0-9_]+$', tabla):
        return jsonify({"error": "Nombre de tabla inválido."}), 400
    conn = get_db_connection('cuadrecaja')
    if not conn:
        return jsonify({"error": "Error de conexión a la base de datos"}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = %s", (tabla,))
        campos = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return jsonify(campos)
    except psycopg2.Error as err:
        return jsonify({"error": f"Error al describir la tabla: {err}"}), 500

@app.route('/obtener_campos_villa')
def obtener_campos_villa():
    tabla = request.args.get('tabla')
    if not tabla or not re.match(r'^[a-zA-Z0-9_]+$', tabla):
        return jsonify({"error": "Nombre de tabla inválido."}), 400
    conn = get_db_connection('villa_colombia')
    if not conn:
        return jsonify({"error": "Error de conexión a la base de datos"}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = %s", (tabla,))
        campos = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return jsonify(campos)
    except psycopg2.Error as err:
        return jsonify({"error": f"Error al describir la tabla: {err}"}), 500

# Otras funciones como datos_porkitos, datos_villa y ejecutar_consulta también necesitan el mismo patrón
# Si deseas que las reemplace por completo, dime y lo hago.

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

...

# Ruta para mostrar datos de Guadalupe
@app.route('/datos_porkitos', methods=['GET', 'POST'])
@login_required
def datos_porkitos():
    fecha_seleccionada = request.form.get('fecha', datetime.now().strftime('%Y-%m-%d'))
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', fecha_seleccionada):
        return "Formato de fecha inválido.", 400

    def ejecutar_consulta(db_name, sql, parametros=None):
        conn = get_db_connection(db_name)
        if not conn:
            return {}
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        try:
            if parametros:
                cursor.execute(sql, parametros)
            else:
                cursor.execute(sql)
            result = cursor.fetchone() or {}
            cursor.close()
            conn.close()
            return result
        except psycopg2.Error as err:
            print(f"Error al ejecutar la consulta: {err}")
            cursor.close()
            conn.close()
            return {}

    discriminacion_data = ejecutar_consulta('cuadrecaja',
        """SELECT SUM(efectivo) AS total_efectivo, SUM(didi_credito) AS total_didi_credito,
        SUM(codigo_qr) AS total_codigo_qr, SUM(total_venta) AS total_venta
        FROM discriminacionventadia WHERE fecha = %s""", (fecha_seleccionada,))

    cierre_data = ejecutar_consulta('cuadrecaja',
        """SELECT SUM(saldo_compras) AS total_saldo_compras, SUM(retiro_efectivo) AS total_retiro_efectivo,
        SUM(efectivo_sede) AS total_efectivo_sede
        FROM cierredia WHERE fecha = %s""", (fecha_seleccionada,))

    efectivo_data = ejecutar_consulta('cuadrecaja',
        """SELECT SUM(base_caja) AS total_base_caja, SUM(efectivo_dia_anterior) AS total_efectivo_anterior,
        SUM(tirilla_z) AS total_tirilla_z
        FROM efectivoiniciodia WHERE fecha = %s""", (fecha_seleccionada,))

    egresos_data = ejecutar_consulta('cuadrecaja',
        """SELECT SUM(Compras) + SUM(Compras_2) + SUM(Compras_3) + SUM(Compras_4) + SUM(Compras_5) AS total_egresos
        FROM egresosdeldia WHERE fecha = %s""", (fecha_seleccionada,))

    venta_didi_data = ejecutar_consulta('cuadrecaja',
        """SELECT SUM(didi_efectivo) AS total_didi_efectivo
        FROM ventadidi WHERE fecha = %s""", (fecha_seleccionada,))

    ventas_hasta_el_momento_data = ejecutar_consulta('cuadrecaja',
        """SELECT SUM(total_venta) AS total_ventas_hasta_ahora
        FROM discriminacionventadia WHERE fecha <= %s""", (fecha_seleccionada,))

    total_efectivo = (discriminacion_data.get('total_efectivo') or 0) + (cierre_data.get('total_efectivo_sede') or 0)
    total_ventas_didi = (discriminacion_data.get('total_didi_credito') or 0) + (venta_didi_data.get('total_didi_efectivo') or 0)
    total_ventas_qr = discriminacion_data.get('total_codigo_qr') or 0
    total_ventas = discriminacion_data.get('total_venta') or 0
    efectivo_restante = total_ventas + (venta_didi_data.get('total_didi_efectivo') or 0) - (total_ventas_didi + total_ventas_qr)
    total_egresos = egresos_data.get('total_egresos') or 0
    total_ventas_hasta_el_momento = ventas_hasta_el_momento_data.get('total_ventas_hasta_ahora') or 0

    return render_template('datos_porkitos.html',
        fecha_seleccionada=fecha_seleccionada,
        total_efectivo=total_efectivo,
        total_ventas_didi=total_ventas_didi,
        total_ventas_qr=total_ventas_qr,
        total_egresos=total_egresos,
        total_ventas=total_ventas,
        efectivo_restante=efectivo_restante,
        total_ventas_hasta_el_momento=total_ventas_hasta_el_momento,
        local="Guadalupe")

...

... 

# Ruta para mostrar datos de Villa Colombia
@app.route('/datos_porkitosVilla', methods=['GET', 'POST'])
@login_required
def datos_porkitos_villa():
    fecha_seleccionada = request.form.get('fecha', datetime.now().strftime('%Y-%m-%d'))
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', fecha_seleccionada):
        return "Formato de fecha inválido.", 400

    def ejecutar_consulta(db_name, sql, parametros=None):
        conn = get_db_connection(db_name)
        if not conn:
            return {}
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        try:
            if parametros:
                cursor.execute(sql, parametros)
            else:
                cursor.execute(sql)
            result = cursor.fetchone() or {}
            cursor.close()
            conn.close()
            return result
        except psycopg2.Error as err:
            print(f"Error al ejecutar la consulta: {err}")
            cursor.close()
            conn.close()
            return {}

    discriminacion_data = ejecutar_consulta('villa_colombia',
        """SELECT SUM(efectivo) AS total_efectivo, SUM(didi_credito) AS total_didi_credito,
        SUM(codigo_qr) AS total_codigo_qr, SUM(total_venta) AS total_venta
        FROM discriminacionventadia WHERE fecha = %s""", (fecha_seleccionada,))

    cierre_data = ejecutar_consulta('villa_colombia',
        """SELECT SUM(saldo_compras) AS total_saldo_compras, SUM(retiro_efectivo) AS total_retiro_efectivo,
        SUM(efectivo_sede) AS total_efectivo_sede
        FROM cierredia WHERE fecha = %s""", (fecha_seleccionada,))

    efectivo_data = ejecutar_consulta('villa_colombia',
        """SELECT SUM(base_caja) AS total_base_caja, SUM(efectivo_dia_anterior) AS total_efectivo_anterior,
        SUM(tirilla_z) AS total_tirilla_z
        FROM efectivoiniciodia WHERE fecha = %s""", (fecha_seleccionada,))

    egresos_data = ejecutar_consulta('villa_colombia',
        """SELECT SUM(Compras) + SUM(Compras_2) + SUM(Compras_3) + SUM(Compras_4) + SUM(Compras_5) AS total_egresos
        FROM egresosdeldia WHERE fecha = %s""", (fecha_seleccionada,))

    venta_didi_data = ejecutar_consulta('villa_colombia',
        """SELECT SUM(didi_efectivo) AS total_didi_efectivo
        FROM ventadidi WHERE fecha = %s""", (fecha_seleccionada,))

    ventas_hasta_el_momento_data = ejecutar_consulta('villa_colombia',
        """SELECT SUM(total_venta) AS total_ventas_hasta_ahora
        FROM discriminacionventadia WHERE fecha <= %s""", (fecha_seleccionada,))

    total_efectivo = (discriminacion_data.get('total_efectivo') or 0) + (cierre_data.get('total_efectivo_sede') or 0)
    total_ventas_didi = (discriminacion_data.get('total_didi_credito') or 0) + (venta_didi_data.get('total_didi_efectivo') or 0)
    total_ventas_qr = discriminacion_data.get('total_codigo_qr') or 0
    total_ventas = discriminacion_data.get('total_venta') or 0
    efectivo_restante = total_ventas + (venta_didi_data.get('total_didi_efectivo') or 0) - (total_ventas_didi + total_ventas_qr)
    total_egresos = egresos_data.get('total_egresos') or 0
    total_ventas_hasta_el_momento = ventas_hasta_el_momento_data.get('total_ventas_hasta_ahora') or 0

    return render_template('datos_porkitosVilla.html',
        fecha_seleccionada=fecha_seleccionada,
        total_efectivo=total_efectivo,
        total_ventas_didi=total_ventas_didi,
        total_ventas_qr=total_ventas_qr,
        total_egresos=total_egresos,
        total_ventas=total_ventas,
        efectivo_restante=efectivo_restante,
        total_ventas_hasta_el_momento=total_ventas_hasta_el_momento,
        local="Villa Colombia")

...

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
