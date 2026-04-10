# ==============================================================================
# SCRIPT 1: CREACIÓN DE LA ARQUITECTURA DE DATOS EN LORCA (NUBE)
# ==============================================================================
# Objetivo: 
# Conectarse a la base de datos de la universidad y crear todas las tablas (cajones)
# vacías, listas para recibir datos. Junta la parte del Clima y la parte de la Web.
# ==============================================================================

import os
import mysql.connector

def main():
    # --------------------------------------------------------
    # 1. CONFIGURACIÓN DE CONEXIÓN A LA NUBE (LORCA)
    # --------------------------------------------------------
    db_host = "10.151.30.2"
    db_port = 3306
    db_user = "bd_rvm_solar_map"
    db_pass = os.getenv("DB_PASS", "Mar123Qz") # Tu contraseña de DBeaver
    db_name = "bd_rvm_solar_map"

    try:
        # Nos conectamos a la base de datos
        conexion = mysql.connector.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_pass,
            database=db_name,
            ssl_disabled=True
        )

        if conexion.is_connected():
            print("1. ¡Conectado a Lorca con éxito!")
            cursor = conexion.cursor()

            # --------------------------------------------------------
            # 2. DESACTIVAR SEGUROS TEMPORALMENTE
            # --------------------------------------------------------
            # Apagamos las "claves foráneas" un segundo para poder crear las
            # tablas en cualquier orden sin que MySQL se queje.
            cursor.execute("SET FOREIGN_KEY_CHECKS=0;")

            # --------------------------------------------------------
            # 3. EL CÓDIGO SQL: CREACIÓN DE TABLAS (DDL)
            # --------------------------------------------------------
            # Todas las sentencias SQL guardadas en un texto largo
            SQL_TABLAS = """
            -- ========================================================
            -- BLOQUE A: TABLAS DIMENSIÓN (Los filtros y agrupadores)
            -- ========================================================

            -- 1. Zonas: La cuadrícula geográfica de Madrid
            CREATE TABLE IF NOT EXISTS dim_zona (
                id_zona VARCHAR(32) PRIMARY KEY,        
                municipio VARCHAR(100) NOT NULL,        
                provincia VARCHAR(100),                 
                altitud DOUBLE,                         
                lat_center DOUBLE NOT NULL,             
                lon_center DOUBLE NOT NULL,             
                norte_lat_max DOUBLE NOT NULL,          
                sur_lat_min DOUBLE NOT NULL,            
                este_lon_max DOUBLE NOT NULL,           
                oeste_lon_min DOUBLE NOT NULL,          
                INDEX idx_limites_mapa (sur_lat_min, norte_lat_max, oeste_lon_min, este_lon_max)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

            -- 2. Fecha: Nuestro calendario personalizado
            CREATE TABLE IF NOT EXISTS dim_fecha (
                id_fecha INT PRIMARY KEY,               -- Ej: 20260228
                fecha_completa DATE NOT NULL,           
                anio SMALLINT NOT NULL,                 
                trimestre TINYINT NOT NULL,             
                mes TINYINT NOT NULL,                   
                nombre_mes VARCHAR(20) NOT NULL,        
                dia TINYINT NOT NULL,                   
                dia_semana TINYINT NOT NULL,            
                nombre_dia VARCHAR(20) NOT NULL,        
                estacion VARCHAR(20) NOT NULL,          
                es_fin_de_semana BOOLEAN NOT NULL,      
                es_festivo BOOLEAN NOT NULL,            
                es_horario_verano BOOLEAN NOT NULL      
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

            -- 3. Hora: El reloj para los perfiles horarios
            CREATE TABLE IF NOT EXISTS dim_hora (
                id_hora INT PRIMARY KEY,                -- Ej: 1430
                hora_del_dia TINYINT NOT NULL,          
                minuto_del_dia TINYINT NOT NULL,        
                hora_formato_24h VARCHAR(5) NOT NULL,   
                hora_formato_12h VARCHAR(8) NOT NULL,   
                tramo_horario VARCHAR(20) NOT NULL      -- Mañana, Tarde, Noche
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

            -- 4. Usuario (WEB): La gente que entra a la página
            CREATE TABLE IF NOT EXISTS dim_usuario (
                id_usuario VARCHAR(64) PRIMARY KEY,     
                tipo_usuario VARCHAR(50) NOT NULL,      -- Anonimo, Premium...
                nombre_completo VARCHAR(50) NOT NULL,
                edad INT NOT NULL,
                cp_usuario INT NOT NULL,
                grupo_usuario VARCHAR(50) NOT NULL,
                fecha_primer_acceso DATE                
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

            -- 5. Sesión (WEB): El parche arreglado. La visita concreta del usuario.
            CREATE TABLE IF NOT EXISTS dim_sesion (
                id_sesion VARCHAR(64) PRIMARY KEY,      
                id_usuario VARCHAR(64) NOT NULL,        
                fecha_inicio DATETIME NOT NULL,         
                dispositivo VARCHAR(50),                -- Móvil, PC...
                navegador VARCHAR(50),                  -- Chrome, Safari...
                ip_origen VARCHAR(50),                  
                CONSTRAINT fk_sesion_usuario FOREIGN KEY (id_usuario) REFERENCES dim_usuario(id_usuario)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

            -- 6. Eventos (WEB): Los botones que pueden pulsar
            CREATE TABLE IF NOT EXISTS dim_tipo_evento (
                id_tipo_evento VARCHAR(64) PRIMARY KEY, 
                fase VARCHAR(50) NOT NULL,              
                pantalla_origen VARCHAR(50) NOT NULL,   
                pantalla_actual VARCHAR(50) NOT NULL,
                accion_fase VARCHAR(100) NOT NULL       
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

            -- 7. Tejados: Físicos y técnicos
            CREATE TABLE IF NOT EXISTS dim_caracteristicas_tejado (
                id_caracteristica INT AUTO_INCREMENT PRIMARY KEY,
                tamano_categoria VARCHAR(50) NOT NULL,  
                orientacion_principal VARCHAR(20),      
                viabilidad_solar VARCHAR(20) NOT NULL   
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

            -- 8. Consumo: Perfiles de gasto eléctrico
            CREATE TABLE IF NOT EXISTS dim_perfil_consumo (
                id_perfil INT AUTO_INCREMENT PRIMARY KEY,
                tipo_usuario VARCHAR(50) NOT NULL,      
                tramo_horario_pico VARCHAR(50) NOT NULL 
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

            -- 9. Economía: Inflación y precios
            CREATE TABLE IF NOT EXISTS dim_escenario_economico (
                id_escenario INT AUTO_INCREMENT PRIMARY KEY,
                tipo_escenario VARCHAR(50) NOT NULL,    
                inflacion_aplicada DOUBLE NOT NULL      
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


            -- ========================================================
            -- BLOQUE B: TABLAS DE HECHOS (Los números y las acciones)
            -- ========================================================

            -- HECHO 1: Clima Diario (Aquí irán tus CSVs)
            CREATE TABLE IF NOT EXISTS fact_clima_diario (
                id_clima BIGINT AUTO_INCREMENT PRIMARY KEY,
                id_zona VARCHAR(32) NOT NULL,           
                id_fecha INT NOT NULL,                  
                radiacion_total_kwh_m2 DOUBLE,          
                temperatura_max_c DOUBLE,               
                temperatura_min_c DOUBLE,               
                cobertura_nubes_promedio DOUBLE,        
                horas_sol_util DOUBLE,                  
                potencial_zona DOUBLE,                  
                CONSTRAINT fk_clima_zona FOREIGN KEY (id_zona) REFERENCES dim_zona(id_zona),
                CONSTRAINT fk_clima_fecha FOREIGN KEY (id_fecha) REFERENCES dim_fecha(id_fecha),
                INDEX idx_busqueda_clima (id_zona, id_fecha)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

            -- HECHO 2: El Tracking de la Web (Los clics)
            CREATE TABLE IF NOT EXISTS fact_eventos_web (
                id_evento BIGINT AUTO_INCREMENT PRIMARY KEY,
                id_usuario VARCHAR(64) NOT NULL,        
                id_sesion VARCHAR(64) NOT NULL,         
                id_tipo_evento VARCHAR(64) NOT NULL,    
                id_zona VARCHAR(32),                    
                id_fecha INT NOT NULL,                  
                id_hora INT NOT NULL,                   
                tiempo_desde_inicio_sesion_seg INT,     
                tiempo_en_pantalla_seg INT,             
                valor_numerico_evento DOUBLE,           
                cantidad_evento INT,
                CONSTRAINT fk_evento_usuario FOREIGN KEY (id_usuario) REFERENCES dim_usuario(id_usuario),
                CONSTRAINT fk_evento_sesion FOREIGN KEY (id_sesion) REFERENCES dim_sesion(id_sesion),
                CONSTRAINT fk_evento_tipo FOREIGN KEY (id_tipo_evento) REFERENCES dim_tipo_evento(id_tipo_evento),
                CONSTRAINT fk_evento_zona FOREIGN KEY (id_zona) REFERENCES dim_zona(id_zona),
                CONSTRAINT fk_evento_fecha FOREIGN KEY (id_fecha) REFERENCES dim_fecha(id_fecha),
                CONSTRAINT fk_evento_hora FOREIGN KEY (id_hora) REFERENCES dim_hora(id_hora),
                INDEX idx_analisis_usuario (id_usuario, id_fecha),
                INDEX idx_analisis_sesion (id_sesion)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4; 

            -- HECHO 3: Tejados Detectados (Inteligencia Artificial)
            CREATE TABLE IF NOT EXISTS fact_tejados_detectados (
                id_tejado BIGINT AUTO_INCREMENT PRIMARY KEY,
                id_zona VARCHAR(32) NOT NULL,           
                id_caracteristica INT NOT NULL,         
                area_util_m2 DOUBLE NOT NULL,           
                inclinacion_grados DOUBLE,              
                factor_sombra_porcentaje DOUBLE,        
                porcentaje_fiabilidad_modelo DOUBLE,    
                potencial_tejado_kwh DOUBLE,            
                numero_paneles INT,                     
                CONSTRAINT fk_tejado_zona FOREIGN KEY (id_zona) REFERENCES dim_zona(id_zona),
                CONSTRAINT fk_tejado_carac FOREIGN KEY (id_caracteristica) REFERENCES dim_caracteristicas_tejado(id_caracteristica),
                INDEX idx_busqueda_tejado_zona (id_zona)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

            -- HECHO 4: Simulación Económica (Euros y rentabilidad)
            CREATE TABLE IF NOT EXISTS fact_simulacion_roi (
                id_simulacion BIGINT AUTO_INCREMENT PRIMARY KEY,
                id_zona VARCHAR(32) NOT NULL,           
                id_tejado BIGINT NOT NULL,              
                id_perfil INT NOT NULL,                 
                id_escenario INT NOT NULL,              
                id_fecha_inicio INT NOT NULL,           
                id_fecha_fin INT NOT NULL,              
                precio_energia_proyectada DOUBLE,       
                coste_instalacion DOUBLE,               
                ahorro_anual DOUBLE,                    
                produccion_anual_kwh DOUBLE,            
                meses_para_amortizar DOUBLE,            
                CONSTRAINT fk_roi_zona FOREIGN KEY (id_zona) REFERENCES dim_zona(id_zona),
                CONSTRAINT fk_roi_tejado FOREIGN KEY (id_tejado) REFERENCES fact_tejados_detectados(id_tejado),
                CONSTRAINT fk_roi_perfil FOREIGN KEY (id_perfil) REFERENCES dim_perfil_consumo(id_perfil),
                CONSTRAINT fk_roi_escenario FOREIGN KEY (id_escenario) REFERENCES dim_escenario_economico(id_escenario),
                CONSTRAINT fk_roi_fecha_inicio FOREIGN KEY (id_fecha_inicio) REFERENCES dim_fecha(id_fecha),
                CONSTRAINT fk_roi_fecha_fin FOREIGN KEY (id_fecha_fin) REFERENCES dim_fecha(id_fecha),
                INDEX idx_busqueda_roi (id_zona, id_tejado)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

            -- HECHO 5: Perfil Horario Típico (Curvas de campana)
            CREATE TABLE IF NOT EXISTS fact_perfil_horario (
                id_perfil_hora BIGINT AUTO_INCREMENT PRIMARY KEY,
                id_zona VARCHAR(32) NOT NULL,           
                mes TINYINT NOT NULL,                   
                id_hora INT NOT NULL,                   
                radiacion_media_hora DOUBLE,            
                temperatura_media_hora DOUBLE,          
                CONSTRAINT fk_perfil_zona FOREIGN KEY (id_zona) REFERENCES dim_zona(id_zona),
                CONSTRAINT fk_perfil_hora FOREIGN KEY (id_hora) REFERENCES dim_hora(id_hora),
                INDEX idx_busqueda_perfil (id_zona, mes)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """

            # --------------------------------------------------------
            # 4. EJECUCIÓN MÁGICA
            # --------------------------------------------------------
            print("2. Construyendo la estructura de tablas en la nube...")
            
            # Cortamos el texto largo por los puntos y comas (;) y ejecutamos uno a uno
            for sentencia in SQL_TABLAS.split(";"):
                if sentencia.strip(): # Si la frase no está en blanco
                    cursor.execute(sentencia)
            
            # Volvemos a encender los seguros de la base de datos
            cursor.execute("SET FOREIGN_KEY_CHECKS=1;")
            conexion.commit()

            print("3. ¡Éxito! Todas las tablas están listas y conectadas entre sí.")

    except mysql.connector.Error as error:
        print(f"❌ Error al hablar con Lorca: {error}")

    finally:
        # Cerramos la puerta al salir
        if 'conexion' in locals() and conexion.is_connected():
            cursor.close()
            conexion.close()
            print("4. Conexión cerrada de forma segura.")

if __name__ == "__main__":
    main()