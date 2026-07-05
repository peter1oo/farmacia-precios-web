"""
Rellena el campo "funcion" de cada producto de la muestra:
- Si La Rebaja aporto una descripcion real del producto, se usa esa
  (fuente: droguera, mas confiable), recortada a un tamano breve.
- Si no, se usa la descripcion redactada por IA (fuente: ia_generado),
  que debe marcarse en la web como no verificada por un profesional.
"""
import json
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent / "data" / "muestra_productos.json"
IA_PATH = Path(__file__).parent / "descripciones_ia.json"
MAX_LARGO = 180


def recortar(texto, largo=MAX_LARGO):
    texto = " ".join(texto.split())
    if len(texto) <= largo:
        return texto
    return texto[:largo].rsplit(" ", 1)[0] + "..."


def main():
    productos = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    descripciones_ia = json.loads(IA_PATH.read_text(encoding="utf-8"))

    for prod in productos:
        desc_real = prod.get("_la_rebaja_descripcion")
        if desc_real:
            prod["funcion"] = recortar(desc_real)
            prod["funcion_fuente"] = "drogueria_competencia"
        else:
            prod["funcion"] = descripciones_ia.get(str(prod["id"]), "Descripción no disponible.")
            prod["funcion_fuente"] = "ia_generado"

    DATA_PATH.write_text(json.dumps(productos, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Funcion asignada a {len(productos)} productos.")


if __name__ == "__main__":
    main()
