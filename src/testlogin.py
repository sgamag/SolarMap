import time
from login import get_token  # ajusta el import si tu módulo se llama distinto

def test_login_cdse():
    print("Probando login con Copernicus Data Space...")

    try:
        token = get_token(force_refresh=True)  # fuerza pedir uno nuevo
        print("\n✅ Token obtenido correctamente.")
        print(f"Inicio del token: {token[:60]}...")  # mostramos solo los primeros caracteres
        print(f"Longitud total del token: {len(token)} caracteres.")

        ahora = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        print(f"Hora actual: {ahora}")
        print("\n💡 Ya puedes usar este token en tus peticiones con 'Authorization: Bearer <token>'")

    except Exception as e:
        print("\n❌ Error al obtener el token:")
        print(e)


if __name__ == "__main__":
    test_login_cdse()
