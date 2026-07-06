"""
Combina catalogo.json + precios_larebaja.json en web/datos.json, y copia la
plantilla estatica a web/index.html (ver seccion 7 del diseno).

Antes de escribir nada, valida que la tasa de match de hoy no haya caido de
forma drastica frente al historial reciente (seccion 6); si cae, aborta y
conserva la publicacion anterior tal cual estaba.

La funcion/descripcion mostrada sigue esta prioridad (ver diseno
2026-07-06-descripciones-ia-design.md):
1. Descripcion real de La Rebaja (funcion_fuente="real").
2. Descripcion generada por IA en el backfill de data/descripciones_ia.json
   (funcion_fuente="ia") -- debe marcarse en la web como no verificada por un
   quimico farmaceutico.
3. Ninguna disponible: funcion y funcion_fuente quedan en None.
"""
import json
import shutil
from datetime import datetime, timezone

import config
import validar_publicacion

PLANTILLA_HTML = config.RAIZ / "scraper" / "plantilla_web.html"


def cargar_precios_larebaja() -> dict:
    try:
        with open(config.PRECIOS_LAREBAJA_JSON, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"meta": {"historial_tasa_match": []}, "productos": {}}


def cargar_descripciones_ia() -> dict:
    try:
        with open(config.DESCRIPCIONES_IA_JSON, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def resolver_funcion(info_larebaja: dict, descripcion_ia: str | None) -> tuple[str | None, str | None]:
    desc_real = info_larebaja.get("descripcion")
    if desc_real:
        return desc_real, "real"
    if descripcion_ia:
        return descripcion_ia, "ia"
    return None, None


def construir_datos(catalogo: list, precios_larebaja: dict, descripciones_ia: dict) -> dict:
    productos_larebaja = precios_larebaja["productos"]

    productos = []
    for p in catalogo:
        info = productos_larebaja.get(p["ean"], {})
        funcion, funcion_fuente = resolver_funcion(info, descripciones_ia.get(p["ean"]))
        productos.append(
            {
                "ean": p["ean"],
                "nombre": p["nombre"],
                "proveedor": p["proveedor"],
                "precio_farmacia": p["precio_farmacia"],
                "precio_larebaja": info.get("precio"),
                "funcion": funcion,
                "funcion_fuente": funcion_fuente,
                "ultima_consulta_larebaja": info.get("ultima_consulta"),
            }
        )

    return {
        "generado": datetime.now(timezone.utc).isoformat(),
        "productos": productos,
    }


def main():
    precios_larebaja = cargar_precios_larebaja()

    publicar, motivo = validar_publicacion.debe_publicar(precios_larebaja["meta"]["historial_tasa_match"])
    print(f"Validacion pre-publicacion: {motivo}")
    if not publicar:
        print("ABORTADO: se conserva la publicacion anterior en web/.")
        return

    with open(config.CATALOGO_JSON, encoding="utf-8") as f:
        catalogo = json.load(f)
    descripciones_ia = cargar_descripciones_ia()

    datos = construir_datos(catalogo, precios_larebaja, descripciones_ia)

    config.WEB_DIR.mkdir(parents=True, exist_ok=True)
    with open(config.WEB_DIR / "datos.json", "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)

    shutil.copyfile(PLANTILLA_HTML, config.WEB_DIR / "index.html")

    con_precio = sum(1 for p in datos["productos"] if p["precio_larebaja"] is not None)
    print(f"Web generada: {len(datos['productos'])} productos, {con_precio} con precio de La Rebaja.")


if __name__ == "__main__":
    main()
