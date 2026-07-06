"""
Fusiona un lote redactado (data/lote_descripciones_redactado.json, formato
{ean: descripcion}) dentro de data/descripciones_ia.json, sin sobreescribir
entradas ya existentes (ver diseno 2026-07-06-descripciones-ia-design.md,
seccion 4).

Uso:
    py scraper/agregar_descripciones_ia.py
"""
import json

import config

LOTE_REDACTADO_JSON = config.DATA_DIR / "lote_descripciones_redactado.json"


def main():
    with open(LOTE_REDACTADO_JSON, encoding="utf-8") as f:
        lote = json.load(f)

    try:
        with open(config.DESCRIPCIONES_IA_JSON, encoding="utf-8") as f:
            descripciones_ia = json.load(f)
    except FileNotFoundError:
        descripciones_ia = {}

    agregadas = 0
    for ean, descripcion in lote.items():
        if ean not in descripciones_ia:
            descripciones_ia[ean] = descripcion
            agregadas += 1

    with open(config.DESCRIPCIONES_IA_JSON, "w", encoding="utf-8") as f:
        json.dump(descripciones_ia, f, ensure_ascii=False, indent=2)

    print(f"Agregadas {agregadas} descripciones nuevas. Total acumulado: {len(descripciones_ia)}.")


if __name__ == "__main__":
    main()
