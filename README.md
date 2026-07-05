# farmacia-precios-web

Compara los precios propios del catálogo completo (16,810 productos) contra Drogas La Rebaja,
y publica el resultado como una web estática para consulta en el punto de venta de las 3 sedes.

Diseño completo: `docs/superpowers/specs/2026-07-05-farmacia-precios-web-design.md`

## Flujo

1. **Local (diario, segundos):** `scraper/extraer_catalogo.py` lee el Excel del catálogo
   (`productos.xls`) y sube `data/catalogo.json` al repositorio.
2. **Nube (GitHub Actions, cron diario ~3 AM):**
   - `scraper/calcular_ranking_ventas.py` — cruce exacto por nombre contra el histórico de
     ventas y ranking de unidades vendidas.
   - `scraper/seleccionar_lote.py` — decide el lote del día (top ventas + franja rotativa).
   - `scraper/scrapear_larebaja.py` — consulta la API de La Rebaja solo para ese lote.
   - `scraper/fusionar_funcion.py` — asigna descripción real o generada por IA.
   - `scraper/generar_web.py` — genera `web/index.html` + `web/datos.json`.
   - Publica en GitHub Pages.

## Configuración local

Ver `scraper/config.py` para las rutas y parámetros (ubicación del Excel, tamaño de lotes, etc.).

## Instalación

```
pip install -r requirements.txt
```
