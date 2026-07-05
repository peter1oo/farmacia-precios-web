"""
Lee productos.xls (catalogo completo de la farmacia) y genera una muestra
aleatoria variada de productos (distintos proveedores) para probar el
sistema de comparacion de precios antes de escalar a todo el catalogo.
"""
import json
import random
from pathlib import Path

import pandas as pd

ORIGEN = Path(r"C:\Users\equipo\Desktop\productos.xls")
DESTINO = Path(__file__).parent.parent / "data" / "muestra_productos.json"
TAMANO_MUESTRA = 150

random.seed(42)

df = pd.read_excel(ORIGEN)
df.columns = [c.strip() for c in df.columns]

# Normalizar tipos
df["Denominación"] = df["Denominación"].astype(str).str.strip()
df["Proveedor"] = df["Proveedor"].astype(str).str.strip()
df["EAN"] = df["EAN"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
df["Venta Real"] = pd.to_numeric(df["Venta Real"], errors="coerce")

df = df.dropna(subset=["Denominación", "Venta Real"])
df = df[df["Denominación"] != ""]

proveedores = df["Proveedor"].unique().tolist()
random.shuffle(proveedores)

filas_muestra = []
restante = TAMANO_MUESTRA

# Reparte la muestra entre proveedores para que sea variada, no concentrada
por_proveedor = max(1, TAMANO_MUESTRA // max(1, len(proveedores)))

for prov in proveedores:
    if restante <= 0:
        break
    grupo = df[df["Proveedor"] == prov]
    n = min(por_proveedor, len(grupo), restante)
    filas_muestra.append(grupo.sample(n=n, random_state=42))
    restante -= n

muestra = pd.concat(filas_muestra) if filas_muestra else df.sample(n=TAMANO_MUESTRA)
muestra = muestra.sample(frac=1, random_state=1).reset_index(drop=True)  # mezclar orden

productos = []
for i, row in muestra.iterrows():
    productos.append({
        "id": i + 1,
        "proveedor": row["Proveedor"],
        "nombre": row["Denominación"],
        "precio_farmacia": float(row["Venta Real"]),
        "ean": row["EAN"],
        "funcion": None,
        "precios_competencia": {
            "cruz_verde": None,
            "la_rebaja": None,
            "farmatodo": None,
        },
    })

DESTINO.parent.mkdir(parents=True, exist_ok=True)
with open(DESTINO, "w", encoding="utf-8") as f:
    json.dump(productos, f, ensure_ascii=False, indent=2)

print(f"Muestra generada: {len(productos)} productos -> {DESTINO}")
print(f"Proveedores distintos representados: {muestra['Proveedor'].nunique()}")
