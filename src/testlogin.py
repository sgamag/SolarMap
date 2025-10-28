# src/test_token.py
"""
Comprueba si la petición de token CDSE funciona correctamente.
Muestra el JSON devuelto y la parte del token que hay que usar en las peticiones.
"""

from login import get_token

def main():
    print("🔐 Probando obtención de token Copernicus (CDSE)...")
    token = get_token()  # usa tus credenciales del .env o las cacheadas
    print("\n✅ Token obtenido correctamente.\n")

    # Mostramos solo los primeros y últimos caracteres para no revelar todo
    print(f"Access token (parcial): {token[:40]}...{token[-10:]}")
    print(f"Longitud del token: {len(token)} caracteres")

    print("\n🧠 IMPORTANTE:")
    print("Esta es la parte del token que debes usar en tus peticiones:")
    print('headers = {"Authorization": f"Bearer <AQUÍ_TU_TOKEN>"}')
    print("\nEjemplo:")
    print(f'Authorization: Bearer {token[:20]}...')

if __name__ == "__main__":
    main()
