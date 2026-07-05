"""
Lee productos.xls (catalogo completo de la farmacia) y genera data/catalogo.json
con el catalogo completo, listo para subirse al repositorio.

Corre localmente cada vez que se reexporta el Excel. No hace scraping ni toca
la competencia -- esa parte corre en GitHub Actions a partir del JSON generado
aqui.

Limpieza aplicada (ver seccion 4 del diseno, hallazgo durante implementacion):
- Se descartan filas promocionales/obsequios (ej. "OBS. KIT POP...",
  "OBSEQUIO...", "KIT VIRT...") -- no son productos vendibles y comparten
  codigos EAN placeholder reutilizados entre decenas de regalos distintos,
  lo que los hace ademas una fuente de EAN ambiguos.
- Se deduplica por EAN, quedandose con la primera fila -- el mismo producto
  puede aparecer varias veces identico en el export (distintos registros de
  inventario del mismo producto).
"""
import json
import re

import pandas as pd

import config

PATRON_PROMOCIONAL = re.compile(r"^OBS\.|^OBSEQUIO|^KIT VIRT|^OBS ", re.IGNORECASE)


def main():
    df = pd.read_excel(config.EXCEL_CATALOGO)
    df.columns = [c.strip() for c in df.columns]

    df["Denominación"] = df["Denominación"].astype(str).str.strip()
    df["Proveedor"] = df["Proveedor"].astype(str).str.strip()
    df["EAN"] = df["EAN"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    df["Venta Real"] = pd.to_numeric(df["Venta Real"], errors="coerce")

    df = df.dropna(subset=["Denominación", "Venta Real"])
    df = df[df["Denominación"] != ""]

    total_antes = len(df)
    df = df[~df["Denominación"].str.contains(PATRON_PROMOCIONAL, regex=True, na=False)]
    descartados_promo = total_antes - len(df)

    antes_dedup = len(df)
    df = df.drop_duplicates(subset="EAN", keep="first")
    descartados_dup = antes_dedup - len(df)

    productos = [
        {
            "ean": row["EAN"],
            "proveedor": row["Proveedor"],
            "nombre": row["Denominación"],
            "precio_farmacia": float(row["Venta Real"]),
        }
        for _, row in df.iterrows()
    ]

    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(config.CATALOGO_JSON, "w", encoding="utf-8") as f:
        json.dump(productos, f, ensure_ascii=False, indent=2)

    print(f"Filas originales: {total_antes}")
    print(f"Descartadas por ser promocionales/obsequios: {descartados_promo}")
    print(f"Descartadas por EAN duplicado: {descartados_dup}")
    print(f"Catalogo final: {len(productos)} productos -> {config.CATALOGO_JSON}")


if __name__ == "__main__":
    main()
