from fastapi import HTTPException
from pydantic import BaseModel
import mysql.connector
import hashlib
from datetime import date

# modelo para recibir datos de la web
class FormularioRegistro(BaseModel):
    id_usuario: str
    nombre: str
    apellidos: str
    email: str
    password: str
    cp_usuario: int
    fecha_nacimiento: str 
    grupo_usuario: str = "Residencial"

# endpoint para registrar
@app.post("/registro-usuario")
async def registrar_usuario(datos: FormularioRegistro):
    password_hash = hashlib.sha256(datos.password.encode()).hexdigest()
    fecha_hoy = date.today().strftime('%Y-%m-%d')

    conn = mysql.connector.connect(
        host="10.151.30.2", user="bd_rvm_solar_map",
        password="Mar123Qz", database="bd_rvm_solar_map"
    )
    cursor = conn.cursor()

    try:
        conn.start_transaction()

        # tabla de la app (datos personales)
        sql_app = """
            INSERT INTO app_credenciales_usuario 
            (id_usuario, nombre, apellidos, email, password_hash)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(sql_app, (datos.id_usuario, datos.nombre, datos.apellidos, datos.email, password_hash))

        # tabla de analitica (anonimo)
        sql_dw = """
            INSERT INTO dim_usuario 
            (id_usuario, fecha_nacimiento, cp_usuario, grupo_usuario, fecha_primer_acceso)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(sql_dw, (datos.id_usuario, datos.fecha_nacimiento, datos.cp_usuario, datos.grupo_usuario, fecha_hoy))

        conn.commit()
        return {"status": "success", "mensaje": "usuario registrado"}

    except mysql.connector.Error as err:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"error en bd: {err}")
    finally:
        cursor.close()
        conn.close()