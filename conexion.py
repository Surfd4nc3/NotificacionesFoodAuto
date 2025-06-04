# conexion.py
import pyodbc
import sys

# Configuración de la base de datos
DB_CONFIG = {
    "myLIMS_Novo_conn": {
        "server": "CMCCLDDB01",
        "database": "myLIMS_Novo",
        "username": "SI$MYLIMS",
        "password": "@M4qBjLs",
        "driver": "{ODBC Driver 17 for SQL Server}" # Asegúrate que este driver es el correcto y está instalado
    },
    "BDClink_conn": {
        "server": "CMCCLDDB01", 
        "database": "BDClink",
        "username": "SI$MYLIMS",
        "password": "@M4qBjLs",
        "driver": "{ODBC Driver 17 for SQL Server}"
    }
}

class ManejadorConexionSQL:
    def __init__(self, nombre_conexion_config):
        self.conexion = None
        self.config_actual = DB_CONFIG.get(nombre_conexion_config)

        if not self.config_actual:
            print(f"❌ Configuración no encontrada para '{nombre_conexion_config}' en DB_CONFIG.")
            raise ValueError(f"Configuración no encontrada para '{nombre_conexion_config}'")

        self.nombre_db_para_logs = self.config_actual.get('database', 'desconocida')

    def conectar(self):
        try:
            partes_conexion = [
                f"DRIVER={self.config_actual['driver']}",
                f"SERVER={self.config_actual['server']}",
                f"DATABASE={self.config_actual['database']}",
            ]
            if self.config_actual.get('integrated_security', False):
                partes_conexion.append("Trusted_Connection=yes") 
            else:
                partes_conexion.append(f"UID={self.config_actual.get('username', '')}")
                partes_conexion.append(f"PWD={self.config_actual.get('password', '')}")
            
            partes_conexion.append("TrustServerCertificate=Yes")
            cadena_conexion_final = ";".join(partes_conexion)
            
            self.conexion = pyodbc.connect(cadena_conexion_final)
            print(f"✅ Conexión exitosa a la base de datos '{self.nombre_db_para_logs}' en el servidor '{self.config_actual['server']}'.")
            return self.conexion
        except pyodbc.Error as ex:
            sqlstate = ex.args[0]
            print(f"❌ Error de conexión a '{self.nombre_db_para_logs}': {ex} (SQLSTATE: {sqlstate})")
            return None

    def ejecutar_consulta(self, query, params=None):
        if not self.conexion:
            print(f"❌ No hay conexión activa para ejecutar la consulta en '{self.nombre_db_para_logs}'.")
            return None 
        
        try:
            with self.conexion.cursor() as cursor:
                # --- CAMBIO IMPORTANTE AQUÍ ---
                # Solo pasar 'params' si realmente existen.
                if params:
                    # print(f"ℹ️ Ejecutando consulta CON parámetros: {params}") # Descomentar para depurar
                    cursor.execute(query, params)
                else:
                    # print(f"ℹ️ Ejecutando consulta SIN parámetros.") # Descomentar para depurar
                    cursor.execute(query) # Ejecutar sin el segundo argumento 'params'
                
                if cursor.description: 
                    column_names = [column[0] for column in cursor.description]
                    rows = cursor.fetchall()
                    return [dict(zip(column_names, row)) for row in rows]
                else: 
                    self.conexion.commit() 
                    return [] 
        except pyodbc.Error as ex:
            print(f"❌ Error al ejecutar la consulta en '{self.nombre_db_para_logs}': {ex}")
            print(f"   Consulta que falló (primeros 200 caracteres): {query[:200]}...")
            if params:
                print(f"   Parámetros: {params}")
            return None

    def cerrar(self):
        if self.conexion:
            try:
                self.conexion.close()
                print(f"🔌 Conexión a '{self.nombre_db_para_logs}' cerrada.")
                self.conexion = None
            except pyodbc.Error as ex:
                print(f"❌ Error al cerrar la conexión a '{self.nombre_db_para_logs}': {ex}")