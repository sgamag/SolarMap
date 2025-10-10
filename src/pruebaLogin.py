# src/test_login.py
from login import get_token

def main():
    print("🔍 Probando autenticación con Copernicus...")

    try:
        token = get_token()
        print("\n✅ Token obtenido correctamente:\n")
        print(token[:150] + "...\n")  # solo mostramos el principio
        print("🔒 (token recortado por seguridad)\n")

    except Exception as e:
        print("❌ Error al obtener el token:")
        print(e)

if __name__ == "__main__":
    main()
