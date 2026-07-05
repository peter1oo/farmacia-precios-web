"""
Cruza el catalogo (productos.xls) contra el historico de ventas/facturacion
(archivo de rotacion) para rankear productos por unidades vendidas.

Se usa UNICAMENTE cruce exacto por nombre normalizado: se probo fuzzy matching
y se descarto porque generaba coincidencias incorrectas (ver seccion 4 del
diseno, ej. confundio catalogos de calibres distintos de un mismo insumo
medico). Los productos vendidos sin match exacto, o nunca vendidos en el
periodo, quedan fuera del ranking y caen en la rotacion pareja.

Corre localmente (no en GitHub Actions) cuando hay un nuevo export de ventas;
su salida (data/ranking_ventas.json) se sube al repositorio como cualquier
otro dato.
"""
import json
import re
import sys
import unicodedata

import pandas as pd

import config


def normalizar(texto: str) -> str:
    texto = str(texto).upper()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    texto = re.sub(r"[^A-Z0-9 ]", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def main():
    catalogo = pd.read_excel(config.EXCEL_CATALOGO)
    catalogo.columns = [c.strip() for c in catalogo.columns]
    catalogo["norm"] = catalogo["Denominación"].apply(normalizar)
    catalogo["EAN"] = catalogo["EAN"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)

    # Un mismo nombre normalizado puede repetirse en varias filas del catalogo
    # (lotes/registros distintos del mismo producto): eso no es ambiguo mientras
    # todas esas filas compartan el mismo EAN. Solo se excluye del cruce cuando
    # un mismo nombre normalizado corresponde a EANs realmente distintos, porque
    # ahi si no hay forma de saber a cual de los dos corresponde una venta.
    eans_por_nombre = catalogo.groupby("norm")["EAN"].nunique()
    nombres_ambiguos = set(eans_por_nombre[eans_por_nombre > 1].index)
    norm_a_ean = {
        row["norm"]: row["EAN"]
        for _, row in catalogo.iterrows()
        if row["norm"] not in nombres_ambiguos
    }

    ventas = pd.read_excel(config.EXCEL_VENTAS)
    ventas.columns = [c.strip() for c in ventas.columns]
    ventas["norm"] = ventas["Nombre Producto"].apply(normalizar)
    for col in ("Cantidad Caja", "Cantidad Blister", "Cantidad Unidad"):
        ventas[col] = pd.to_numeric(ventas[col], errors="coerce").fillna(0)
    ventas["unidades"] = ventas["Cantidad Caja"] + ventas["Cantidad Blister"] + ventas["Cantidad Unidad"]

    ventas["ean"] = ventas["norm"].map(norm_a_ean)
    productos_vendidos_unicos = ventas["norm"].nunique()
    con_match = ventas.loc[ventas["ean"].notna(), "norm"].nunique()
    tasa_cruce = con_match / productos_vendidos_unicos if productos_vendidos_unicos else 0

    print(f"Productos vendidos unicos: {productos_vendidos_unicos}")
    print(f"Con cruce exacto al catalogo: {con_match} ({tasa_cruce:.1%})")

    if tasa_cruce < 0.5:
        print(
            "AVISO: la tasa de cruce cayo por debajo del 50% "
            "(referencia esperada: ~80.8%). Revisa si cambio el formato "
            "de alguno de los dos archivos antes de confiar en este ranking.",
            file=sys.stderr,
        )

    ranking = (
        ventas.dropna(subset=["ean"])
        .groupby("ean", as_index=False)["unidades"].sum()
        .rename(columns={"unidades": "unidades_vendidas"})
        .sort_values("unidades_vendidas", ascending=False)
        .reset_index(drop=True)
    )

    salida = {
        "generado": pd.Timestamp.now().isoformat(),
        "tasa_cruce": round(tasa_cruce, 4),
        "productos_rankeados": [
            {"ean": row["ean"], "unidades_vendidas": float(row["unidades_vendidas"])}
            for _, row in ranking.iterrows()
        ],
    }

    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(config.RANKING_VENTAS_JSON, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)

    print(f"Ranking generado: {len(ranking)} productos -> {config.RANKING_VENTAS_JSON}")


if __name__ == "__main__":
    main()
