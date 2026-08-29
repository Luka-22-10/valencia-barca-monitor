import requests
import re
import os
import json
from datetime import datetime

URL = "https://entradas.valenciacf.com/valenciacf_webservices/select/2964323"

DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "")
ESTADO_FILE = "ultima_disponibilidad.json"


def avisar(mensaje):
    if not DISCORD_WEBHOOK:
        print("❌ DISCORD_WEBHOOK NO ESTÁ CONFIGURADO")
        return False

    try:
        respuesta = requests.post(
            DISCORD_WEBHOOK,
            json={"content": mensaje},
            timeout=15
        )

        print(f"Discord respondió con código: {respuesta.status_code}")

        return respuesta.status_code in (200, 204)

    except Exception as e:
        print(f"❌ Error enviando a Discord: {e}")
        return False


def obtener_pagina():
    respuesta = requests.get(
        URL,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "es-ES,es;q=0.9"
        },
        timeout=30
    )

    respuesta.raise_for_status()

    return respuesta.text


def limpiar_texto(texto):
    texto = re.sub(r"<[^>]+>", " ", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def comprobar():
    html = obtener_pagina()

    # Convertimos el HTML en texto legible.
    texto = limpiar_texto(html)

    disponibles = []

    # Busca:
    # SECTOR
    # Desde: 120,00 €
    # 2 entradas disponibles
    #
    # El patrón es deliberadamente flexible porque
    # la página puede cambiar ligeramente.

    patron = re.compile(
        r"(.{3,120}?)"
        r"(?:Desde|Des de|From)"
        r"\s*:?"
        r"\s*"
        r"€?\s*"
        r"([\d.,]+)"
        r"\s*€?"
        r"\s*"
        r"(\d+)"
        r"\s+"
        r"(?:entradas?|tickets?)"
        r"\s+"
        r"(?:disponibles|available)",
        re.IGNORECASE
    )

    for coincidencia in patron.finditer(texto):
        sector = coincidencia.group(1).strip()
        precio = coincidencia.group(2)
        cantidad = int(coincidencia.group(3))

        if cantidad <= 0:
            continue

        # Limpiamos posibles restos del texto anterior.
        sector = re.sub(
            r".{0,80}(?:Ordenado por precio|Sort by price)",
            "",
            sector,
            flags=re.IGNORECASE
        ).strip()

        disponibles.append({
            "sector": sector,
            "precio": precio,
            "cantidad": cantidad
        })

    # Eliminar duplicados
    unicos = []
    vistos = set()

    for entrada in disponibles:
        clave = (
            entrada["sector"].lower(),
            entrada["precio"],
            entrada["cantidad"]
        )

        if clave not in vistos:
            vistos.add(clave)
            unicos.append(entrada)

    return unicos


def cargar_estado():
    if not os.path.exists(ESTADO_FILE):
        return []

    try:
        with open(ESTADO_FILE, "r", encoding="utf-8") as archivo:
            return json.load(archivo)
    except Exception:
        return []


def guardar_estado(entradas):
    with open(ESTADO_FILE, "w", encoding="utf-8") as archivo:
        json.dump(entradas, archivo, ensure_ascii=False, indent=2)


def crear_claves(entradas):
    return sorted(
        f"{e['sector']}|{e['precio']}|{e['cantidad']}"
        for e in entradas
    )


if __name__ == "__main__":

    ahora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    try:
        disponibles = comprobar()

        print(f"[{ahora}] Entradas detectadas: {len(disponibles)}")

        for entrada in disponibles:
            print(
                f"- {entrada['sector']} | "
                f"{entrada['precio']} € | "
                f"{entrada['cantidad']} disponibles"
            )

        anteriores = cargar_estado()

        estado_actual = crear_claves(disponibles)
        estado_anterior = crear_claves(anteriores)

        if disponibles and estado_actual != estado_anterior:

            mensaje = (
                "🚨 **ENTRADAS DISPONIBLES – VALENCIA CF vs BARÇA** 🚨\n\n"
                f"🕐 Comprobado: {ahora}\n\n"
            )

            for entrada in disponibles:
                mensaje += (
                    f"🎟️ **{entrada['sector']}**\n"
                    f"💶 Desde: {entrada['precio']} €\n"
                    f"🎫 Disponibles: **{entrada['cantidad']}**\n\n"
                )

            mensaje += f"🔗 {URL}"

            avisar(mensaje)

        elif not disponibles:
            print("No se han detectado entradas.")

        else:
            print("Disponibilidad sin cambios. No se envía otro aviso.")

        guardar_estado(disponibles)

    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")
        raise
