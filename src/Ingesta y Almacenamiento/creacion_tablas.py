# ==============================================================================
# SCRIPT 1: CREACIÓN DE LA ARQUITECTURA DE DATOS EN LORCA (NUBE) - VERSIÓN BLINDADA
# ==============================================================================

import os
import mysql.connector

def main():
    db_host = "10.151.30.2"
    db_port = 3306
    db_user = "bd_rvm_solar_map"
    db_pass = os.getenv("DB_PASS", "Mar123Qz") 
    db_name = "bd_rvm_solar_map"

    try:
        conexion = mysql.connector.connect(
            host=db_host, port=db_port, user=db_user,
            password=db_pass, database=db_name, ssl_disabled=True
        )

        if conexion.is_connected():
            print("1. ¡Conectado a Lorca con éxito!")
            cursor = conexion.cursor()
            cursor.execute("SET FOREIGN_KEY_CHECKS=0;")

            SQL_TABLAS = """
            -- ========================================================
            -- BLOQUE A: TABLAS DIMENSIÓN
            -- ========================================================
            CREATE TABLE IF NOT EXISTS dim_zona (
                id_zona VARCHAR(32) PRIMARY KEY,        -- ej: "tile_00_00" (Identificador único del cuadrante)
                municipio VARCHAR(100) NOT NULL,        -- ej: "Getafe" (Extraído de OpenStreetMap Nominatim)
                provincia VARCHAR(100),                 -- ej: "Madrid" (Extraído de OpenStreetMap Nominatim)
                lat_center DOUBLE NOT NULL,             -- ej: 40.308 (Latitud del centro exacto del tile)
                lon_center DOUBLE NOT NULL,             -- ej: -3.732 (Longitud del centro exacto del tile)
                norte_lat_max DOUBLE NOT NULL,          -- ej: 40.35 (Límite superior del rectángulo del tile)
                sur_lat_min DOUBLE NOT NULL,            -- ej: 40.25 (Límite inferior del rectángulo del tile)
                este_lon_max DOUBLE NOT NULL,           -- ej: -3.65 (Límite derecho del rectángulo del tile)
                oeste_lon_min DOUBLE NOT NULL,          -- ej: -3.85 (Límite izquierdo del rectángulo del tile)
                INDEX idx_limites_mapa (sur_lat_min, norte_lat_max, oeste_lon_min, este_lon_max)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

            CREATE TABLE IF NOT EXISTS dim_fecha (
                id_fecha INT PRIMARY KEY,               -- ej: 20260315 (Formato YYYYMMDD para búsquedas rápidas)
                fecha_completa DATE NOT NULL,           -- ej: "2026-03-15" (Formato estándar de base de datos)
                año SMALLINT NOT NULL,                  -- ej: 2026 
                trimestre TINYINT NOT NULL,             -- ej: 1 (Primer trimestre del año)
                mes TINYINT NOT NULL,                   -- ej: 3 (Marzo)
                nombre_mes VARCHAR(20) NOT NULL,        -- ej: "Marzo"
                dia TINYINT NOT NULL,                   -- ej: 15
                dia_semana TINYINT NOT NULL,            -- ej: 7 (Domingo)
                nombre_dia VARCHAR(20) NOT NULL,        -- ej: "Domingo"
                estacion VARCHAR(20) NOT NULL,          -- ej: "Invierno" o "Primavera"
                es_fin_de_semana BOOLEAN NOT NULL,      -- ej: 1 (True) o 0 (False)
                es_festivo BOOLEAN NOT NULL,            -- ej: 0 (No es fiesta en Madrid)
                es_horario_verano BOOLEAN NOT NULL      -- ej: 0 (Horario de invierno)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

            CREATE TABLE IF NOT EXISTS dim_hora (
                id_hora INT PRIMARY KEY,                -- ej: 14 (Identificador de la hora)
                hora_del_dia TINYINT NOT NULL,          -- ej: 14 (Hora militar 0-23)
                minuto_del_dia TINYINT NOT NULL,        -- ej: 0 (Siempre 0 en nuestro caso al ser por horas enteras)
                hora_formato_24h VARCHAR(5) NOT NULL,   -- ej: "14:00"
                tramo_horario VARCHAR(20) NOT NULL      -- ej: "Tarde", "Mañana", "Madrugada"
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

            CREATE TABLE IF NOT EXISTS dim_usuario (
                id_usuario VARCHAR(64) PRIMARY KEY,     -- ej: "usr_9876abc" (Hash o ID autogenerado al registrarse)
                tipo_usuario VARCHAR(50) NOT NULL,      -- ej: "Particular", "Comunidad de Vecinos", "Empresa"
                nombre_completo VARCHAR(50) NOT NULL,   -- ej: "Javier Mohino" (Nombre introducido en el registro)
                fecha_nacimiento DATE NOT NULL,          -- ej: "2026/06/15"   
                cp_usuario INT NOT NULL,                -- ej: 28901 (Código Postal de facturación/residencia)
                grupo_usuario VARCHAR(50) NOT NULL,     -- ej: "Joven", "Adulto", "Senior"
                fecha_primer_acceso DATE                -- ej: "2026-03-01" (Día que creó la cuenta en la web)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

            CREATE TABLE IF NOT EXISTS dim_sesion (
                id_sesion VARCHAR(64) PRIMARY KEY,      -- ej: "ses_xyz123" (Token de la sesión web actual)
                id_usuario VARCHAR(64) NOT NULL,        -- ej: "usr_9876abc" (A quién pertenece la sesión)
                fecha_inicio DATETIME NOT NULL,         -- ej: "2026-03-15 14:30:00" (Cuándo entró a la web)
                dispositivo VARCHAR(50),                -- ej: "Smartphone", "Desktop PC"
                navegador VARCHAR(50),                  -- ej: "Chrome", "Safari", "Firefox"
                ip_origen VARCHAR(50),                  -- ej: "192.168.1.55" (Dirección IP de conexión)
                CONSTRAINT fk_sesion_usuario FOREIGN KEY (id_usuario) REFERENCES dim_usuario(id_usuario)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

            CREATE TABLE IF NOT EXISTS dim_tipo_evento (
                id_tipo_evento VARCHAR(64) PRIMARY KEY, -- ej: "ev_click_simular" (Identificador de la acción)
                fase VARCHAR(50) NOT NULL,              -- ej: "Onboarding", "Simulación", "Cierre"
                pantalla_origen VARCHAR(50) NOT NULL,   -- ej: "Home", "Mapa Interactivo" (Dónde estaba)
                pantalla_actual VARCHAR(50) NOT NULL,   -- ej: "Resultados ROI", "Dashboard" (A dónde fue)
                accion_fase VARCHAR(100) NOT NULL       -- ej: "Hizo click en 'Calcular Ahorro'", "Descargó PDF"
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

            CREATE TABLE IF NOT EXISTS dim_caracteristicas_tejado (
                id_caracteristica INT AUTO_INCREMENT PRIMARY KEY, -- ej: 1 (ID numérico autogenerado)
                tamaño_categoria VARCHAR(50) NOT NULL,  -- ej: "Pequeño (<50m2)", "Mediano", "Grande"
                orientacion_principal VARCHAR(20),      -- ej: "Sur", "Suroeste" (Hacia dónde miran las aguas)
                viabilidad_solar VARCHAR(20) NOT NULL   -- ej: "Óptima", "Regular", "No Viable" (Por sombras/inclinación)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

            CREATE TABLE IF NOT EXISTS dim_perfil_consumo (
                id_perfil INT AUTO_INCREMENT PRIMARY KEY, -- ej: 1
                nombre_perfil VARCHAR(50) NOT NULL,      -- ej: "Teletrabajo", "Industrial" (El que elige en el dropdown)
                tramo_horario_pico VARCHAR(50) NOT NULL -- ej: "Tarde/Noche" o "Diurno" (Cuándo pone la lavadora)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

            CREATE TABLE IF NOT EXISTS dim_escenario_economico (
                id_escenario INT AUTO_INCREMENT PRIMARY KEY, -- ej: 2
                tipo_escenario VARCHAR(50) NOT NULL,    -- ej: "Escenario Base", "Inflación Alta" (Para cruzar en ROI)
                inflacion_aplicada DOUBLE NOT NULL      -- ej: 0.04 (Es decir, un 4% de inflación anual estimada)
                tasa_subvencion DOUBLE NOT NULL         -- ej: 0.00 de subvencion
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

            --dimension paneles  - modelo - precio por panel - precio fijo


            -- ========================================================
            -- BLOQUE B: TABLAS DE HECHOS
            -- ========================================================
            CREATE TABLE IF NOT EXISTS fact_clima_diario (
                id_clima BIGINT AUTO_INCREMENT PRIMARY KEY, -- ej: 1025678 (Auto-ticket de la BBDD)
                id_fecha INT NOT NULL,                  -- ej: 20050112 (Conecta con calendario)
                id_zona VARCHAR(32) NOT NULL,           -- ej: "tile_00_00" (Conecta con el cuadrante del mapa)
                id_hora INT NOT NULL,                   -- ej: 12 (Conecta con las 12:00)
                temperatura_hora DOUBLE,               -- ej: 15.5 (Extraído del CSV ERA5)
                radiacion_solar DOUBLE,                 -- ej: 0.85 kWh/m2 (Extraído del CSV ERA5)
                cobertura_nubes DOUBLE,                 -- ej: 0.14 (14% de cielo tapado, desde CSV ERA5)
                potencial_solar DOUBLE,                 -- ej: 0.2436 (Cálculo matemático bruto inicial)
                CONSTRAINT fk_clima_zona FOREIGN KEY (id_zona) REFERENCES dim_zona(id_zona),
                CONSTRAINT fk_clima_fecha FOREIGN KEY (id_fecha) REFERENCES dim_fecha(id_fecha),
                CONSTRAINT fk_clima_hora FOREIGN KEY (id_hora) REFERENCES dim_hora(id_hora),
                UNIQUE KEY uk_antiduplicados (id_fecha, id_zona, id_hora),
                INDEX idx_busqueda_clima (id_zona, id_fecha)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

            CREATE TABLE IF NOT EXISTS fact_eventos_web (
                id_evento BIGINT AUTO_INCREMENT PRIMARY KEY, -- ej: 502 (Auto-ticket)
                id_usuario VARCHAR(64) NOT NULL,        -- ej: "usr_9876abc" (Quién hizo click)
                id_sesion VARCHAR(64) NOT NULL,         -- ej: "ses_xyz123" (En qué visita a la web)
                id_tipo_evento VARCHAR(64) NOT NULL,    -- ej: "ev_click_simular" (Qué botón pulsó)
                id_zona VARCHAR(32),                    -- ej: "tile_00_00" (Si pinchó en una zona concreta del mapa)
                id_fecha INT NOT NULL,                  -- ej: 20260315 (Día del click)
                id_hora INT NOT NULL,                   -- ej: 14 (Hora del click)
                tiempo_desde_inicio_sesion_seg INT,     -- ej: 120 (Tardó 2 minutos en hacer este click)
                tiempo_en_pantalla_seg INT,             -- ej: 45 (Estuvo 45s mirando el mapa antes del click)
                valor_numerico_evento DOUBLE,           -- ej: 5000 (Si el evento era "Meter presupuesto manual")
                cantidad_evento INT,                    -- ej: 1 (Número de veces que hizo click en el botón)
                CONSTRAINT fk_evento_usuario FOREIGN KEY (id_usuario) REFERENCES dim_usuario(id_usuario),
                CONSTRAINT fk_evento_sesion FOREIGN KEY (id_sesion) REFERENCES dim_sesion(id_sesion),
                CONSTRAINT fk_evento_tipo FOREIGN KEY (id_tipo_evento) REFERENCES dim_tipo_evento(id_tipo_evento),
                CONSTRAINT fk_evento_zona FOREIGN KEY (id_zona) REFERENCES dim_zona(id_zona),
                CONSTRAINT fk_evento_fecha FOREIGN KEY (id_fecha) REFERENCES dim_fecha(id_fecha),
                CONSTRAINT fk_evento_hora FOREIGN KEY (id_hora) REFERENCES dim_hora(id_hora),
                INDEX idx_analisis_usuario (id_usuario, id_fecha),
                INDEX idx_analisis_sesion (id_sesion)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4; 

            CREATE TABLE IF NOT EXISTS fact_tejados_detectados (
                id_tejado BIGINT AUTO_INCREMENT PRIMARY KEY, -- ej: 55 (Ticket único del tejado)
                id_zona VARCHAR(32) NOT NULL,           -- ej: "tile_00_00" (En qué pueblo está el tejado)
                id_caracteristica INT NOT NULL,         -- ej: 1 (Conecta con "Pequeño, Sur, Óptimo")
                area_util_m2 DOUBLE NOT NULL,           -- ej: 45.5 (Metros REAles donde caben placas. Output modelo tejados)
                orientacion_grados DOUBLE,              -- ej: 175.00 (casi sur perfecto)
                porcentaje_fiabilidad_modelo DOUBLE,    -- ej: 0.95 (La IA está 95% segura de que es un tejado)
                potencial_tejado_kwh DOUBLE,            -- ej: 4500.5 (Cálculo: radiacion * area_util)
                numero_paneles INT,                     -- ej: 10 (Cálculo estandarizado: área útil / 2m2 por panel)
                CONSTRAINT fk_tejado_zona FOREIGN KEY (id_zona) REFERENCES dim_zona(id_zona),
                CONSTRAINT fk_tejado_carac FOREIGN KEY (id_caracteristica) REFERENCES dim_caracteristicas_tejado(id_caracteristica),
                INDEX idx_busqueda_tejado_zona (id_zona)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

            CREATE TABLE IF NOT EXISTS fact_simulacion_roi (
                id_simulacion BIGINT AUTO_INCREMENT PRIMARY KEY, -- ej: 88 (Ticket único de la simulación)
                id_zona VARCHAR(32) NOT NULL,           -- ej: "tile_00_00" (Contexto geográfico)
                id_tejado BIGINT NOT NULL,              -- ej: 55 (Qué tejado estamos simulando)
                id_perfil INT NOT NULL,                 -- ej: 1 (Residencial Tarde/Noche)
                id_escenario INT NOT NULL,              -- ej: 2 (Escenario inflación base)
                id_fecha_inicio INT NOT NULL,           -- ej: 20260101 (Año simulado inicial)
                id_fecha_fin INT NOT NULL,              -- ej: 20510101 (Año simulado final - vida útil paneles)
                precio_energia_proyectada DOUBLE,       -- ej: 0.15 €/kWh (Lo que dará el Modelo de Luz de Eva)
                coste_instalacion DOUBLE,               -- ej: 5000.0 € (Nº paneles * Precio unitario instalación)
                ahorro_anual DOUBLE,                    -- ej: 1200.5 € (Generación * Precio energía * Factor perfil consumo)
                produccion_anual_kwh DOUBLE,            -- ej: 4500.0 kWh (La energía real aprovechada)
                meses_para_amortizar DOUBLE,            -- ej: 50.0 (Meses hasta recuperar los 5000€ invertidos)
                CONSTRAINT fk_roi_zona FOREIGN KEY (id_zona) REFERENCES dim_zona(id_zona),
                CONSTRAINT fk_roi_tejado FOREIGN KEY (id_tejado) REFERENCES fact_tejados_detectados(id_tejado),
                CONSTRAINT fk_roi_perfil FOREIGN KEY (id_perfil) REFERENCES dim_perfil_consumo(id_perfil),
                CONSTRAINT fk_roi_escenario FOREIGN KEY (id_escenario) REFERENCES dim_escenario_economico(id_escenario),
                CONSTRAINT fk_roi_fecha_inicio FOREIGN KEY (id_fecha_inicio) REFERENCES dim_fecha(id_fecha),
                CONSTRAINT fk_roi_fecha_fin FOREIGN KEY (id_fecha_fin) REFERENCES dim_fecha(id_fecha),
                INDEX idx_busqueda_roi (id_zona, id_tejado)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

            -- OJO: Modificado el nombre y añadida la variable potencial como hablamos
            CREATE TABLE IF NOT EXISTS fact_clima_agregado_mensual (
                id_agregacion BIGINT AUTO_INCREMENT PRIMARY KEY, -- ej: 123 (Ticket automático)
                id_zona VARCHAR(32) NOT NULL,           -- ej: "tile_00_00"
                mes TINYINT NOT NULL,                   -- ej: 1 (Enero)
                id_hora INT NOT NULL,                   -- ej: 12 (Las 12:00 del mediodía)
                radiacion_media_hora DOUBLE,            -- ej: 0.65 (La media histórica de sol a esa hora en ese mes)
                temperatura_media_hora DOUBLE,          -- ej: 8.5 (La temperatura media histórica)
                potencial_medio_hora DOUBLE,            -- ej: 0.18 (El rendimiento base medio precalculado)
                CONSTRAINT fk_agregado_zona FOREIGN KEY (id_zona) REFERENCES dim_zona(id_zona),
                CONSTRAINT fk_agregado_hora FOREIGN KEY (id_hora) REFERENCES dim_hora(id_hora),
                INDEX idx_busqueda_agregado (id_zona, mes)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """

            print("2. Construyendo la estructura de tablas en la nube (Versión Segura)...")
            for sentencia in SQL_TABLAS.split(";"):
                if sentencia.strip(): 
                    cursor.execute(sentencia)
            
            cursor.execute("SET FOREIGN_KEY_CHECKS=1;")
            conexion.commit()
            print("3. ¡Éxito! Base de datos blindada contra duplicados.")

    except mysql.connector.Error as error:
        print(f"❌ Error al hablar con Lorca: {error}")
    finally:
        if 'conexion' in locals() and conexion.is_connected():
            cursor.close()
            conexion.close()
            print("4. Conexión cerrada.")

if __name__ == "__main__":
    main()