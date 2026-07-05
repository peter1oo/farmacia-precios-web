"""
Busca cada producto de la muestra en la API publica de Drogas La Rebaja
(plataforma VTEX) y guarda el precio y una breve descripcion cuando la
tienda la publica.

Primero intenta hacer match exacto por EAN (mas confiable). Si no
encuentra nada, intenta una busqueda de texto por nombre como respaldo.

Es respetuoso con el sitio de la competencia: una peticion a la vez,
con una pausa entre productos para no sobrecargar su servidor.
"""
import json
import re
import time
from html import unescape
from pathlib import Path

import requests

DATA_PATH = Path(__file__).parent.parent / "data" / "muestra_productos.json"
BASE_URL = "https://www.larebajavirtual.com/api/catalog_system/pub/products/search"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ConsultaPreciosFarmacia/1.0)"}
PAUSA_SEGUNDOS = 0.6


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
    if not ean or ean.lower() == "nan":
        return None
    try:
        r = requests.get(BASE_URL, params={"fq": f"alternateIds_Ean:{ean}"},
                          headers=HEADERS, timeout=10)
        r.raise_for_status()
        resultados = r.json()
    except Exception:
        return None
    return resultados or None


def buscar_por_texto(nombre):
    consulta = " ".join(nombre.split()[:4])  # primeras palabras del nombre
    try:
        r = requests.get(BASE_URL, params={"ft": consulta},
                          headers=HEADERS, timeout=10)
        r.raise_for_status()
        resultados = r.json()
    except Exception:
        return None
    return resultados or None


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


def main():
    productos = json.loads(DATA_PATH.read_text(encoding="utf-8"))

    encontrados = 0
    for i, prod in enumerate(productos, start=1):
        resultados = buscar_por_ean(prod["ean"])
        metodo = "ean"
        if not resultados:
            resultados = buscar_por_texto(prod["nombre"])
            metodo = "texto"

        precio, info = extraer_info(resultados)
        if precio is not None:
            prod["precios_competencia"]["la_rebaja"] = precio
            prod["_la_rebaja_metodo_match"] = metodo
            if info and info.get("descripcion"):
                prod["_la_rebaja_descripcion"] = info["descripcion"]
            if info and info.get("principio_activo"):
                prod["_la_rebaja_principio_activo"] = info["principio_activo"]
            encontrados += 1

        print(f"[{i}/{len(productos)}] {prod['nombre'][:45]:45s} -> "
              f"{'ENCONTRADO ($' + str(precio) + ', ' + metodo + ')' if precio else 'sin match'}")

        time.sleep(PAUSA_SEGUNDOS)

    DATA_PATH.write_text(json.dumps(productos, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nListo. {encontrados}/{len(productos)} productos con precio de La Rebaja encontrado.")


if __name__ == "__main__":
    main()
