import requests
import re
import os
from datetime import datetime

PAGINA_ENTRADAS = "https://www.valenciacf.com/entradas"

URLS_VENTA = [
    "https://entradas.valenciacf.com/valenciacf_webservices/select/2964323",
    "https://entradas.valenciacf.com/valenciacf_webservices/select/2964323?hl=es-ES",
    "https://entradas.valenciacf.com/valenciacf_webservices/select/2964323?hl=ca-ES-valencia",
    "https://entradas.valenciacf.com/valenciacf_webservices/select/2964323?hl=en-US",
    "https://entradas.valenciacf.com/valenciacf_webservices/select/2964323?viewCode=V_blockmap_view",
    "https://entradas.valenciacf.com/valenciacf_webservices/select/2964323?hl=en-US&viewCode=V_blockmap_view",
    "https://entradas.valenciacf.com/valenciacf_webservices/select/2964323?hl=ca-ES-valencia&viewCode=V_blockmap_view",
]

DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/139.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Referer": PAGINA_ENTRADAS,
}


def avisar(mensaje):
    if not DISCORD_WEBHOOK:
        print("❌ DISCORD_WEBHOOK NO ESTÁ CONFIGURADO")
        return

    try:
        respuesta = requests.post(
            DISCORD_WEBHOOK,
            json={"content": mensaje},
            timeout=15
        )

        print(
            f"Discord respondió con código: "
            f"{respuesta.status_code}"
        )

    except Exception as e:
        print(f"❌ Error enviando a Discord: {e}")


def comprobar_pagina_principal():
    print("🌐 Comprobando página principal de Valencia CF...")

    try:
        respuesta = requests.get(
            PAGINA_ENTRADAS,
            headers=HEADERS,
            timeout=30
        )

        print(
            f"Página principal → HTTP "
            f"{respuesta.status_code}"
        )

        respuesta.raise_for_status()

        texto = respuesta.text.lower()

        if "barcelona" in texto:
            print("✅ Valencia-Barça encontrado en la página oficial.")
            return True

        print("⚠️ Valencia-Barça no aparece en el HTML principal.")
        return False

    except requests.RequestException as e:
        print(f"❌ Error en página principal: {e}")
        return False


def limpiar_html(html):
    texto = re.sub(r"<script.*?</script>", " ", html,
                   flags=re.IGNORECASE | re.DOTALL)

    texto = re.sub(r"<style.*?</style>", " ", texto,
                   flags=re.IGNORECASE | re.DOTALL)

    texto = re.sub(r"<[^>]+>", " ", texto)

    texto = re.sub(r"\s+", " ", texto)

    return texto.strip()


def extraer_disponibilidad(texto):
    resultados = []

    # Busca bloques del tipo:
    #
    # TRIBUNA PREF. 212 - 212
    # Desde: 260,00 €
    # 1 entradas disponibles

    patron = re.compile(
        r"(.{3,120}?)"
        r"(?:Desde|Des de|From)"
        r"\s*:?\s*"
        r"(?:€\s*)?"
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

        # Limpiamos restos innecesarios.
        sector = re.sub(
            r"^(.*?)(?:TRIBUNA|SECTOR|GOL|GRADA|ANFITEATRO|S\. GOL)",
            lambda m: m.group(0),
            sector,
            flags=re.IGNORECASE
        )

        resultados.append({
            "sector": sector,
            "precio": precio,
            "cantidad": cantidad
        })

    # Eliminar duplicados
    unicos = []
    vistos = set()

    for entrada in resultados:

        clave = (
            entrada["sector"].lower(),
            entrada["precio"],
            entrada["cantidad"]
        )

        if clave not in vistos:
            vistos.add(clave)
            unicos.append(entrada)

    return unicos


def comprobar_ventas():
    encontrados = []
    errores_403 = 0
    errores_otros = 0
    accesibles = 0

    for url in URLS_VENTA:

        print(f"\n🔎 Probando:")
        print(url)

        try:

            respuesta = requests.get(
                url,
                headers=HEADERS,
                timeout=30
            )

            print(
                f"Resultado HTTP: "
                f"{respuesta.status_code}"
            )

            if respuesta.status_code == 403:
                print("⛔ 403 — variante rechazada.")
                errores_403 += 1
                continue

            if respuesta.status_code != 200:
                print("⚠️ Respuesta diferente de 200.")
                errores_otros += 1
                continue

            accesibles += 1

            texto = limpiar_html(respuesta.text)

            disponibilidad = extraer_disponibilidad(texto)

            if disponibilidad:

                print(
                    f"🎟️ ¡Disponibilidad encontrada! "
                    f"{len(disponibilidad)} sectores."
                )

                encontrados.extend(disponibilidad)

            else:
                print(
                    "Sin entradas disponibles detectadas "
                    "en esta variante."
                )

        except requests.RequestException as e:

            print(
                f"❌ Error de conexión: {e}"
            )

            errores_otros += 1

    # Eliminar duplicados entre variantes
    resultado_final = []
    vistos = set()

    for entrada in encontrados:

        clave = (
            entrada["sector"].lower(),
            entrada["precio"],
            entrada["cantidad"]
        )

        if clave not in vistos:
            vistos.add(clave)
            resultado_final.append(entrada)

    if resultado_final:
        return resultado_final, errores_403, errores_otros, accesibles

    return [], errores_403, errores_otros, accesibles


if __name__ == "__main__":

    ahora = datetime.now().strftime(
        "%d/%m/%Y %H:%M:%S"
    )

    print("=" * 60)
    print("🎟️ MONITOR VALENCIA CF - FC BARCELONA")
    print(f"🕐 {ahora}")
    print("=" * 60)

    # --------------------------------------------------
    # 1. Página principal
    # --------------------------------------------------

    comprobar_pagina_principal()

    # --------------------------------------------------
    # 2. Variantes de venta
    # --------------------------------------------------

    disponibles, errores_403, errores_otros, accesibles = (
        comprobar_ventas()
    )

    print("\n" + "=" * 60)

    # --------------------------------------------------
    # 3. Resultado
    # --------------------------------------------------

    if disponibles:

        print(
            f"🚨 SE HAN DETECTADO "
            f"{len(disponibles)} SECTORES CON ENTRADAS"
        )

        mensaje = (
            "🚨 **ENTRADAS DISPONIBLES – VALENCIA CF vs BARÇA** 🚨\n\n"
            f"🕐 {ahora}\n\n"
        )

        for entrada in disponibles[:15]:

            mensaje += (
                f"🎟️ **{entrada['sector']}**\n"
                f"💶 Desde: **{entrada['precio']} €**\n"
                f"🎫 Disponibles: **{entrada['cantidad']}**\n\n"
            )

        mensaje += (
            "🔗 Página oficial:\n"
            "https://entradas.valenciacf.com/"
            "valenciacf_webservices/select/2964323"
        )

        avisar(mensaje)

    else:

        if errores_403 == len(URLS_VENTA):

            print(
                "⛔ TODAS LAS VARIANTES OFICIALES "
                "DEVOLVIERON 403."
            )

            avisar(
                "⚠️ **MONITOR VALENCIA-BARÇA**\n\n"
                "No se ha podido comprobar la disponibilidad "
                "porque todas las variantes oficiales de venta "
                "han respondido con HTTP 403.\n\n"
                "No se han generado falsos avisos."
            )

        elif accesibles > 0:

            print(
                "✅ Variantes accesibles comprobadas."
            )

            print(
                "🎟️ No se han detectado entradas."
            )

        else:

            print(
                "⚠️ No se ha podido comprobar ninguna "
                "variante correctamente."
            )

    print("=" * 60)
