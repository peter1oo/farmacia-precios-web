"""
Calcula que productos del catalogo todavia no tienen ninguna descripcion
(ni real de La Rebaja, ni generada por IA) y escribe el siguiente lote a
redactar (ver diseno 2026-07-06-descripciones-ia-design.md, seccion 4).

Uso:
    py scraper/reportar_sin_descripcion.py [--tam 300]

Escribe data/lote_descripciones_pendiente.json con una lista de
{ean, nombre, proveedor} del tamano pedido. Se puede correr repetidas veces:
cada corrida excluye los EAN que ya tienen descripcion (real o IA) al momento
de ejecutarse.
"""
import argparse
import json

import config

LOTE_PENDIENTE_JSON = config.DATA_DIR / "lote_descripciones_pendiente.json"


def cargar_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def calcular_pendientes(catalogo, precios_larebaja, descripciones_ia):
    productos_larebaja = precios_larebaja["productos"]
    pendientes = []
    for p in catalogo:
        info = productos_larebaja.get(p["ean"], {})
        tiene_real = bool(info.get("descripcion"))
        tiene_ia = bool(descripciones_ia.get(p["ean"]))
        if not tiene_real and not tiene_ia:
            pendientes.append({"ean": p["ean"], "nombre": p["nombre"], "proveedor": p["proveedor"]})
    return pendientes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tam", type=int, default=300)
    args = parser.parse_args()

    catalogo = cargar_json(config.CATALOGO_JSON, [])
    precios_larebaja = cargar_json(config.PRECIOS_LAREBAJA_JSON, {"productos": {}})
    descripciones_ia = cargar_json(config.DESCRIPCIONES_IA_JSON, {})

    pendientes = calcular_pendientes(catalogo, precios_larebaja, descripciones_ia)
    lote = pendientes[: args.tam]

    with open(LOTE_PENDIENTE_JSON, "w", encoding="utf-8") as f:
        json.dump(lote, f, ensure_ascii=False, indent=2)

    print(f"Pendientes totales: {len(pendientes)}")
    print(f"Lote escrito ({len(lote)} productos): {LOTE_PENDIENTE_JSON}")


if __name__ == "__main__":
    main()
