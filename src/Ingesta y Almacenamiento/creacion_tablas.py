#Script de creacion de la arquitectura de datos analitica 

import os
import mysql.connector

# Configuracion de la conexion al servidor Lorca
DB_HOST = "10.151.30.2"
DB_PORT = 3306
DB_USER = "bd_rvm_solar_map"
DB_PASS = os.getenv("DB_PASS", "Mar123Qz")
DB_NAME = "bd_rvm_solar_map"

# Definicion de las tablas en SQL
# El orden: primero las dimensiones, luego las tablas de hechos,
# ya que las tablas de hechos referencian a las dimensiones con claves foraneas.

TABLAS_SQL = [

    #  TABLAS DIMENSIONES

    # Zonas geograficas: los 36 tiles de 8x8 km que cubren la Comunidad de Madrid.
    # Varios tiles pueden compartir municipio.
    """
    CREATE TABLE IF NOT EXISTS dim_zona (
        id_zona             VARCHAR(32)     PRIMARY KEY,
        municipio           VARCHAR(100)    NOT NULL,
        provincia           VARCHAR(100)    NOT NULL DEFAULT 'Madrid',
        comunidad_autonoma  VARCHAR(100)    NOT NULL DEFAULT 'Comunidad de Madrid',
        lat_center          DOUBLE          NOT NULL,
        lon_center          DOUBLE          NOT NULL,
        norte_lat_max       DOUBLE          NOT NULL,
        sur_lat_min         DOUBLE          NOT NULL,
        este_lon_max        DOUBLE          NOT NULL,
        oeste_lon_min       DOUBLE          NOT NULL,
        potencial_medio     DOUBLE,
        INDEX idx_limites_mapa (sur_lat_min, norte_lat_max, oeste_lon_min, este_lon_max)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    # Calendario con todas las fechas del periodo de analisis hasta el momento (2025-2026).
    """
    CREATE TABLE IF NOT EXISTS dim_fecha (
        id_fecha            INT             PRIMARY KEY,
        fecha_completa      DATE            NOT NULL,
        año                 SMALLINT        NOT NULL,
        trimestre           TINYINT         NOT NULL,
        mes                 TINYINT         NOT NULL,
        nombre_mes          VARCHAR(20)     NOT NULL,
        dia                 TINYINT         NOT NULL,
        dia_semana          TINYINT         NOT NULL,
        nombre_dia          VARCHAR(20)     NOT NULL,
        estacion            VARCHAR(20)     NOT NULL,
        es_fin_de_semana    BOOLEAN         NOT NULL,
        es_festivo          BOOLEAN         NOT NULL,
        es_horario_verano   BOOLEAN         NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    # Dimension hora con agrupacion en tramos horarios para el dashboard de usuario.
    """
    CREATE TABLE IF NOT EXISTS dim_hora (
        id_hora             INT             PRIMARY KEY,
        hora_formato_24h    VARCHAR(5)      NOT NULL,
        tramo_horario       VARCHAR(20)     NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    # Perfiles de usuario anonimos para el Data Warehouse.
    # Los campos demograficos permiten NULL para albergar a los usuarios no registrados.
    """
    CREATE TABLE IF NOT EXISTS dim_usuario (
        id_usuario          VARCHAR(64)     PRIMARY KEY,
        fecha_nacimiento    DATE            NULL,
        cp_usuario          INT             NULL,
        grupo_usuario       VARCHAR(50)     NULL,
        fecha_primer_acceso DATE            NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    # Tabla transaccional (OLTP) para la gestion de la web y control de accesos (RGPD).
    # Se separa de dim_usuario para mantener el modelo analitico anonimo y seguro.
    """
    CREATE TABLE IF NOT EXISTS app_credenciales_usuario (
        id_usuario          VARCHAR(64)     PRIMARY KEY,
        nombre              VARCHAR(100)    NOT NULL,
        apellidos           VARCHAR(150)    NOT NULL,
        email               VARCHAR(255)    NOT NULL UNIQUE,
        password_hash       VARCHAR(255)    NOT NULL,
        
        CONSTRAINT fk_credenciales_usuario FOREIGN KEY (id_usuario) REFERENCES dim_usuario(id_usuario) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    # Catalogo de eventos web que puede registrar el sistema.
    # Se ha eliminado el evento de salida artificial para medir el churn real.
    """
    CREATE TABLE IF NOT EXISTS dim_tipo_evento (
        id_tipo_evento      VARCHAR(64)     PRIMARY KEY,
        pantalla_origen     VARCHAR(50)     NULL,
        pantalla_actual     VARCHAR(50)     NOT NULL,
        nombre_evento       VARCHAR(100)    NOT NULL,
        es_hito_importante  BOOLEAN         NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    # Combinaciones de tamaño y orientacion de tejado para clasificar
    # los tejados detectados por el modelo de IA.
    """
    CREATE TABLE IF NOT EXISTS dim_caracteristicas_tejado (
        id_caracteristica   INT             AUTO_INCREMENT PRIMARY KEY,
        tamaño_categoria    VARCHAR(50)     NOT NULL,
        orientacion_principal VARCHAR(20)   NOT NULL,
        horas_sol            INT            NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    # Los tres escenarios economicos que el usuario puede consultar en el simulador.
    """
    CREATE TABLE IF NOT EXISTS dim_escenario_economico (
        id_escenario          INT             PRIMARY KEY,
        nombre_escenario      VARCHAR(50)     NOT NULL,
        banda_prediccion      VARCHAR(20)     NOT NULL,
        descripcion_tendencia VARCHAR(150)    NOT NULL,
        precio_medio_luz      DOUBLE          NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    # Catalogo de paneles solares disponibles en el simulador.
    """
    CREATE TABLE IF NOT EXISTS dim_panel (
        id_panel                        INT             PRIMARY KEY,
        modelo_panel                    VARCHAR(100)    NOT NULL,
        potencia_w                      INT             NOT NULL,
        precio_unitario_euros           DOUBLE          NOT NULL,
        area_panel_m2                   DOUBLE          NOT NULL,
        coste_instalacion_fijo_euros    DOUBLE          NOT NULL,
        nombre_proveedor                VARCHAR(100)    NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
        CREATE TABLE IF NOT EXISTS precio_luz (
            id_prediccion INT AUTO_INCREMENT PRIMARY KEY,
            año INT NOT NULL,
            mes TINYINT NOT NULL,
            precio_luz DOUBLE NOT NULL,
            escenario VARCHAR(50) NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,


    # TABLAS DE HECHOS

    # Datos climaticos historicos agregados a nivel mensual por zona.
    """
    CREATE TABLE IF NOT EXISTS fact_clima_agregado_mensual (
        id_agregacion           BIGINT      AUTO_INCREMENT PRIMARY KEY,
        id_zona                 VARCHAR(32) NOT NULL,
        mes                     TINYINT     NOT NULL,
        radiacion_media_mes     DOUBLE,
        nubosidad_media_mes     DOUBLE,
        temperatura_media_mes   DOUBLE,
        temperatura_maxima_mes  DOUBLE,
        temperatura_minima_mes  DOUBLE,

        UNIQUE KEY uk_zona_mes (id_zona, mes),
        CONSTRAINT fk_agregado_zona FOREIGN KEY (id_zona) REFERENCES dim_zona(id_zona),
        INDEX idx_busqueda_agregado (id_zona, mes)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    # Registro de todos los eventos de comportamiento del usuario en la web.
    """
    CREATE TABLE IF NOT EXISTS fact_eventos_web (
        id_evento                   BIGINT      AUTO_INCREMENT PRIMARY KEY,
        id_usuario                  VARCHAR(64) NOT NULL,
        id_sesion                   VARCHAR(64) NOT NULL,
        id_tipo_evento              VARCHAR(64) NOT NULL,
        id_zona                     VARCHAR(32) NULL,
        id_fecha                    INT         NOT NULL,
        id_hora                     INT         NOT NULL,
        timestamp_evento            DATETIME    NOT NULL,
        duracion_evento_segundos    INT,
        orden_en_sesion             SMALLINT    NOT NULL DEFAULT 0,

        CONSTRAINT fk_evento_usuario    FOREIGN KEY (id_usuario)        REFERENCES dim_usuario(id_usuario),
        CONSTRAINT fk_evento_tipo       FOREIGN KEY (id_tipo_evento)    REFERENCES dim_tipo_evento(id_tipo_evento),
        CONSTRAINT fk_evento_zona       FOREIGN KEY (id_zona)           REFERENCES dim_zona(id_zona),
        CONSTRAINT fk_evento_fecha      FOREIGN KEY (id_fecha)          REFERENCES dim_fecha(id_fecha),
        CONSTRAINT fk_evento_hora       FOREIGN KEY (id_hora)           REFERENCES dim_hora(id_hora),

        INDEX idx_analisis_usuario  (id_usuario, id_fecha),
        INDEX idx_analisis_sesion   (id_sesion),
        INDEX idx_orden_embudo      (id_sesion, orden_en_sesion)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    # Tejados detectados a partir de datos procesados por el modelo de IA.
    """
    CREATE TABLE IF NOT EXISTS fact_tejados_detectados (
        id_tejado               BIGINT      AUTO_INCREMENT PRIMARY KEY,
        id_zona                 VARCHAR(32) NOT NULL,
        id_caracteristica       INT         NOT NULL,
        latitud                 DOUBLE      NOT NULL,
        longitud                DOUBLE      NOT NULL,
        area_total_bruta_m2     DOUBLE      NOT NULL,
        area_util_m2            DOUBLE      NOT NULL,
        orientacion_grados      DOUBLE,
        orientacion_principal   VARCHAR(20),
        potencial_final         DOUBLE,

        CONSTRAINT fk_tejado_zona           FOREIGN KEY (id_zona)           REFERENCES dim_zona(id_zona),
        CONSTRAINT fk_tejado_caracteristica FOREIGN KEY (id_caracteristica)  REFERENCES dim_caracteristicas_tejado(id_caracteristica),

        INDEX idx_busqueda_zona (id_zona)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    # Resultados de cada simulacion ROI ejecutada por un usuario.
    """
    CREATE TABLE IF NOT EXISTS fact_simulacion_roi (
        id_simulacion               BIGINT      AUTO_INCREMENT PRIMARY KEY,
        id_tejado                   BIGINT      NOT NULL,
        id_usuario                  VARCHAR(64) NOT NULL,
        id_sesion                   VARCHAR(64) NULL,

        timestamp_simulacion        DATETIME    NOT NULL,

        CONSTRAINT fk_roi_tejado    FOREIGN KEY (id_tejado)     REFERENCES fact_tejados_detectados(id_tejado),
        CONSTRAINT fk_roi_usuario   FOREIGN KEY (id_usuario)    REFERENCES dim_usuario(id_usuario),

        INDEX idx_analisis_amortizacion (id_tejado)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """
]

def main():
    try:
        conexion = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
            ssl_disabled=True
        )

        if conexion.is_connected():
            print("Conectado a Lorca con exito.")
            cursor = conexion.cursor()

            # Desactivamos temporalmente las claves foraneas para poder crear
            # las tablas en cualquier orden sin errores de dependencias.
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")

            print("Creando tablas...")
            for sentencia in TABLAS_SQL:
                if sentencia.strip():
                    cursor.execute(sentencia)

            # Volvemos a activar la comprobacion de claves foraneas.
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
            conexion.commit()
            print("Todas las tablas creadas correctamente en bd_rvm_solar_map.")

    except mysql.connector.Error as error:
        print(f"Error al conectar con la base de datos: {error}")

    finally:
        if 'conexion' in locals() and conexion.is_connected():
            cursor.close()
            conexion.close()
            print("Conexion cerrada.")

if __name__ == "__main__":
    main()