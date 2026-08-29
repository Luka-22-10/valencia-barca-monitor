import requests
import re
import os
from datetime import datetime

URL = "https://www.valenciacf.com/entradas"

DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "")


def avisar(mensaje):
    if not DISCORD_WEBHOOK:
        print("❌ DISCORD_WEBHOOK NO ESTÁ CONFIGURADO")
        return

    print("✅ DISCORD_WEBHOOK está configurado")

    respuesta = requests.post(
        DISCORD_WEBHOOK,
        json={"content": mensaje},
        timeout=15
    )

    print(f"Discord respondió con código: {respuesta.status_code}")


def comprobar():
    respuesta = requests.get(
        URL,
        headers={
            "User-Agent": "Mozilla/5.0"
        },
        timeout=20
    )

    texto = re.sub(r"\s+", " ", respuesta.text.lower())

    agotado = any(x in texto for x in [
        "agotado",
        "sin entradas",
        "no hay entradas",
        "no disponible"
    ])

    disponible = any(x in texto for x in [
        "comprar",
        "entradas disponibles",
        "seleccionar asiento"
    ])

    return disponible and not agotado


if __name__ == "__main__":
    ahora = datetime.now().strftime("%d/%m/%Y %H:%M")

    

    try:
        if comprobar():
            avisar(
                f"🚨 POSIBLES ENTRADAS DISPONIBLES\n"
                f"Valencia CF vs Barça\n"
                f"Comprobado: {ahora}\n"
                f"{URL}"
            )
            print("¡Posible disponibilidad!")
        else:
            print(f"[{ahora}] No se han detectado entradas.")

    except Exception as e:
        print(f"Error: {e}")
