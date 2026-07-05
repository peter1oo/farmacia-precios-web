"""
Decide que productos se scrapean hoy contra La Rebaja (ver seccion 5 del
diseno): el tier "siempre" (los mas vendidos) se scrapea todos los dias: el
resto del catalogo rota en 7 franjas fijas, una por dia de la semana, para
cubrir el 100% del catalogo cada semana sin depender de guardar un cursor de
estado entre ejecuciones.

Corre en GitHub Actions justo antes del scraping.
"""
import hashlib
import json
from datetime import date, datetime

import config


def franja_de(ean: str, num_franjas: int = config.NUM_FRANJAS) -> int:
    """Franja determinista de un EAN: mismo EAN -> misma franja siempre."""
    digest = hashlib.md5(str(ean).encode("utf-8")).hexdigest()
    return int(digest, 16) % num_franjas


def seleccionar(catalogo: list, ranking_ventas: list, hoy: date) -> dict:
    eans_catalogo = [p["ean"] for p in catalogo]

    top_ordenado = sorted(ranking_ventas, key=lambda r: r["unidades_vendidas"], reverse=True)
    eans_con_ranking_validos = [r["ean"] for r in top_ordenado if r["ean"] in set(eans_catalogo)]
    eans_top_siempre = set(eans_con_ranking_validos[: config.TOP_SIEMPRE])

    resto = [ean for ean in eans_catalogo if ean not in eans_top_siempre]
    franja_hoy = hoy.weekday() % config.NUM_FRANJAS
    eans_franja_hoy = {ean for ean in resto if franja_de(ean) == franja_hoy}

    eans_a_scrapear = eans_top_siempre | eans_franja_hoy

    return {
        "fecha": hoy.isoformat(),
        "franja_hoy": franja_hoy,
        "total_catalogo": len(eans_catalogo),
        "total_top_siempre": len(eans_top_siempre),
        "total_franja_hoy": len(eans_franja_hoy),
        "total_a_scrapear": len(eans_a_scrapear),
        "eans_a_scrapear": sorted(eans_a_scrapear),
    }


def main():
    with open(config.CATALOGO_JSON, encoding="utf-8") as f:
        catalogo = json.load(f)

    try:
        with open(config.RANKING_VENTAS_JSON, encoding="utf-8") as f:
            ranking_ventas = json.load(f)["productos_rankeados"]
    except FileNotFoundError:
        ranking_ventas = []

    lote = seleccionar(catalogo, ranking_ventas, datetime.now().date())

    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(config.LOTE_HOY_JSON, "w", encoding="utf-8") as f:
        json.dump(lote, f, ensure_ascii=False, indent=2)

    print(
        f"Franja {lote['franja_hoy']} | top siempre: {lote['total_top_siempre']} | "
        f"franja hoy: {lote['total_franja_hoy']} | total a scrapear: {lote['total_a_scrapear']} "
        f"de {lote['total_catalogo']}"
    )


if __name__ == "__main__":
    main()
