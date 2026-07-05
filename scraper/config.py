"""
Rutas y parametros centralizados del pipeline. Los scripts que corren solo en
el computador local (extraccion de Excel) leen las rutas de variables de
entorno, con el valor por defecto que usa esta droguería hoy. Los scripts que
corren en GitHub Actions no usan las rutas de Excel: solo leen los JSON ya
subidos a data/.
"""
import os
from pathlib import Path

RAIZ = Path(__file__).parent.parent

# --- Origenes locales (solo para los scripts que corren en el computador local) ---
EXCEL_CATALOGO = Path(os.environ.get(
    "FARMACIA_EXCEL_CATALOGO", r"C:\Users\equipo\Desktop\productos.xls"
))
EXCEL_VENTAS = Path(os.environ.get(
    "FARMACIA_EXCEL_VENTAS", r"C:\Users\equipo\Downloads\asdasdas.xlsx"
))

# --- Datos compartidos (subidos/leidos desde el repositorio) ---
DATA_DIR = RAIZ / "data"
CATALOGO_JSON = DATA_DIR / "catalogo.json"
RANKING_VENTAS_JSON = DATA_DIR / "ranking_ventas.json"
PRECIOS_LAREBAJA_JSON = DATA_DIR / "precios_larebaja.json"
LOTE_HOY_JSON = DATA_DIR / "lote_hoy.json"

WEB_DIR = RAIZ / "web"

# --- Priorizacion y rotacion de lotes (ver seccion 5 del diseno) ---
TOP_SIEMPRE = 1500          # productos mas vendidos que se actualizan todos los dias
NUM_FRANJAS = 7             # una franja rotativa por dia de la semana

# --- Scraping contra La Rebaja ---
PAUSA_ENTRE_PRODUCTOS_SEG = 0.6
MAX_REINTENTOS = 2
ESPERA_REINTENTO_SEG = 1.5

# --- Validacion pre-publicacion ---
# Si la tasa de match del dia cae por debajo de esta fraccion de la tasa
# promedio reciente, se aborta la publicacion y se conserva la anterior.
UMBRAL_CAIDA_MATCH = 0.5
