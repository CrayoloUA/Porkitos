import mysql.connector

config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'julian2006',
    'database': 'cuadrecaja'
}

try:
    conn = mysql.connector.connect(**config)
    cursor = conn.cursor()
    
    # Prueba una consulta simple
    cursor.execute("SHOW TABLES")
    tablas = cursor.fetchall()
    
    print("¡Conexión exitosa!")
    print("Tablas en tu base de datos:")
    for tabla in tablas:
        print(tabla[0])
        
    cursor.close()
    conn.close()
except Exception as e:
    print(f"Error de conexión: {e}")