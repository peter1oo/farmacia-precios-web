"""
Consulta la API publica de Drogas La Rebaja (VTEX) solo para el lote de hoy
(ver seccion 5 y 6 del diseno) y fusiona el resultado en el cache acumulado
data/precios_larebaja.json, preservando lo que no se toco hoy.

Primero intenta match exacto por EAN; si no hay resultado, cae a busqueda de
texto por nombre. Ante fallos de red reintenta con espera progresiva; si se
agotan los reintentos, el precio anterior conocido se conserva tal cual (no
se borra ni se pone en null) y el producto queda registrado como fallido en
el resumen de la corrida.

Es respetuoso con el sitio de la competencia: una peticion a la vez, con una
pausa entre productos.
"""
import json
import os
import re
import time
from datetime import date
from html import unescape
from urllib.parse import quote

import requests

import config

BASE_URL = "https://www.larebajavirtual.com/api/catalog_system/pub/products/search"
# El sitio bloquea la busqueda por texto (400 "Scripts are not allowed!") si el
# User-Agent no parece un navegador real; la busqueda por EAN es mas permisiva
# pero se usan los mismos headers realistas en ambas por consistencia.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Referer": "https://www.larebajavirtual.com/",
}


class ConsultaFallida(Exception):
    pass


def limpiar_html(texto):
    if not texto:
        return None
    texto = re.sub(r"<[^>]+>", " ", texto)
    return unescape(texto).strip() or None


def mejor_precio(producto_vtex):
    mejor = None
    for item in producto_vtex.get("items", []):
        for seller in item.get("sellers", []):
            oferta = seller.get("commertialOffer", {})
            precio = oferta.get("Price")
            disponible = oferta.get("IsAvailable")
            if precio and disponible and (mejor is None or precio < mejor):
                mejor = precio
    return mejor


def buscar_por_ean(ean):
    if not ean or str(ean).lower() == "nan":
        return None
    r = requests.get(BASE_URL, params={"fq": f"alternateIds_Ean:{ean}"}, headers=HEADERS, timeout=10)
    r.raise_for_status()
    return r.json() or None


def buscar_por_texto(nombre):
    # El sitio rechaza (400) los espacios codificados como "+" (lo que hace
    # requests por defecto al pasar params=dict); solo acepta "%20".
    consulta = " ".join(nombre.split()[:4])
    url = f"{BASE_URL}?ft={quote(consulta)}"
    r = requests.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()
    return r.json() or None


def extraer_info(resultados):
    if not resultados:
        return None, None
    candidatos = [(mejor_precio(p), p) for p in resultados]
    candidatos = [(precio, p) for precio, p in candidatos if precio is not None]
    if not candidatos:
        return None, None
    precio, producto = min(candidatos, key=lambda x: x[0])
    descripcion = None
    if producto.get("DescripcionContenido"):
        descripcion = limpiar_html(producto["DescripcionContenido"][0])
    principio_activo = producto.get("Principio activo", [None])[0]
    return precio, {"descripcion": descripcion, "principio_activo": principio_activo}


def consultar_con_reintentos(ean, nombre):
    """Devuelve (precio, info, metodo). Lanza ConsultaFallida si se agotan
    los reintentos por errores de red (no confundir con "sin resultado")."""
    ultimo_error = None
    for intento in range(config.MAX_REINTENTOS + 1):
        try:
            resultados = buscar_por_ean(ean)
            metodo = "ean"
            if not resultados:
                resultados = buscar_por_texto(nombre)
                metodo = "texto"
            precio, info = extraer_info(resultados)
            return precio, info, metodo
        except requests.RequestException as e:
            ultimo_error = e
            if intento < config.MAX_REINTENTOS:
                time.sleep(config.ESPERA_REINTENTO_SEG * (intento + 1))
    raise ConsultaFallida(str(ultimo_error))


def cargar_cache() -> dict:
    try:
        with open(config.PRECIOS_LAREBAJA_JSON, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"meta": {"historial_tasa_match": []}, "productos": {}}


def guardar_cache_atomico(cache: dict):
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    temporal = config.PRECIOS_LAREBAJA_JSON.with_suffix(".tmp")
    with open(temporal, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    os.replace(temporal, config.PRECIOS_LAREBAJA_JSON)


def fusionar_resultado(entrada: dict, precio, info, metodo: str, hoy: str) -> dict:
    """Fusiona el resultado de una consulta exitosa (con o sin match) en la
    entrada de cache existente del producto, sin perder lo que ya habia."""
    entrada = dict(entrada)
    entrada["ultima_consulta"] = hoy
    if precio is not None:
        entrada["precio"] = precio
        entrada["metodo_match"] = metodo
        entrada["disponible"] = True
        if info and info.get("descripcion"):
            entrada["descripcion"] = info["descripcion"]
        if info and info.get("principio_activo"):
            entrada["principio_activo"] = info["principio_activo"]
    else:
        entrada["disponible"] = False
    return entrada


def main():
    with open(config.CATALOGO_JSON, encoding="utf-8") as f:
        catalogo_por_ean = {p["ean"]: p for p in json.load(f)}

    with open(config.LOTE_HOY_JSON, encoding="utf-8") as f:
        lote = json.load(f)

    cache = cargar_cache()
    productos_cache = cache["productos"]
    hoy = date.today().isoformat()

    encontrados = fallidos = sin_resultado = 0
    total = len(lote["eans_a_scrapear"])

    for i, ean in enumerate(lote["eans_a_scrapear"], start=1):
        producto = catalogo_por_ean.get(ean)
        if producto is None:
            continue

        try:
            precio, info, metodo = consultar_con_reintentos(ean, producto["nombre"])
        except ConsultaFallida as e:
            fallidos += 1
            print(f"[{i}/{total}] {producto['nombre'][:45]:45s} -> FALLO DE RED ({e}), se conserva precio anterior")
            continue

        entrada = fusionar_resultado(productos_cache.get(ean, {}), precio, info, metodo, hoy)
        if precio is not None:
            encontrados += 1
            estado = f"ENCONTRADO (${precio}, {metodo})"
        else:
            sin_resultado += 1
            estado = "sin match hoy"

        productos_cache[ean] = entrada
        print(f"[{i}/{total}] {producto['nombre'][:45]:45s} -> {estado}")

        time.sleep(config.PAUSA_ENTRE_PRODUCTOS_SEG)

    tasa_match_hoy = encontrados / total if total else 0
    cache["meta"]["historial_tasa_match"] = (
        cache["meta"].get("historial_tasa_match", []) + [{"fecha": hoy, "tasa_match": round(tasa_match_hoy, 4)}]
    )[-14:]

    guardar_cache_atomico(cache)

    print(
        f"\nListo. {encontrados} encontrados, {sin_resultado} sin resultado, "
        f"{fallidos} fallidos de red, de {total} consultados hoy."
    )
    print(f"Tasa de match hoy: {tasa_match_hoy:.1%}")


if __name__ == "__main__":
    main()
