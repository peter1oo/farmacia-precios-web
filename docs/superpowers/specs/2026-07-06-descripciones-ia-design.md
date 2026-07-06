# Diseño: descripciones generadas por IA para el catálogo completo

Fecha: 2026-07-06

## 1. Contexto

El diseño original (`2026-07-05-farmacia-precios-web-design.md`) dejó como limitación conocida que
solo los productos con descripción real de La Rebaja tienen el campo `funcion` en `web/datos.json`.
Hoy eso son 989 de 13,997 productos (7.1%); el resto queda sin descripción.

El prototipo original (`scraper/3_fusionar_funcion.py` + `scraper/descripciones_ia.json`) tenía el
concepto de una descripción de respaldo generada por IA, pero como archivo estático redactado a mano
para una muestra de 150 productos — nunca se integró al pipeline de producción
(`scraper/generar_web.py`). La plantilla web (`scraper/plantilla_web.html`) ya tiene el disclaimer y
la lógica de badge pensados para distinguir "verificado" (descripción real) de "no verificado" (IA,
debe confirmarse con el químico farmacéutico), pero el badge actual muestra "sin descripción" en vez
de "no verificado" cuando falta el campo.

**Objetivo confirmado:** que todos los productos del catálogo tengan una descripción — a manera de
conocimiento general para el vendedor en el punto de venta, no como indicación clínica. El usuario
entiende y acepta que las descripciones generadas por IA deben marcarse como no verificadas y
confirmarse con un químico farmacéutico antes de comunicarse como asesoría clínica.

## 2. Decisiones confirmadas

- **Modo de ejecución:** backfill local, una sola vez. No se integra generación por IA al workflow
  diario de GitHub Actions — evita depender de una API key en la nube y mantiene el costo/control en
  el computador local.
- **Motor de generación:** Claude (esta sesión de trabajo), sin llamada a una API externa. Se procesa
  por lotes dentro de la conversación; el resultado se persiste incrementalmente para que el proceso
  sea reanudable entre lotes o entre sesiones.
- **Manejo de incertidumbre:** cuando el nombre del producto no da pistas claras del principio activo
  o uso, se redacta la descripción más plausible de mejor esfuerzo (categoría aparente, tipo de
  producto), sin inventar dosis ni indicaciones clínicas específicas. Siempre queda marcada como no
  verificada, igual que el resto de las generadas por IA.
- **Estilo y largo:** una frase corta, ~80-150 caracteres, en el mismo tono que las descripciones
  reales que ya trae La Rebaja.
- **Alcance temporal:** productos nuevos que aparezcan en el catálogo en el futuro no reciben
  descripción automáticamente — quedan sin descripción hasta que se corra el backfill de nuevo
  manualmente. No es parte de este diseño automatizar esa detección continua.

## 3. Arquitectura

```
data/catalogo.json ─────┐
data/precios_larebaja.json ─┤→ scraper/generar_web.py → web/datos.json (funcion + funcion_fuente)
data/descripciones_ia.json ─┘
```

- **`data/descripciones_ia.json`** (nuevo): mapa `EAN → descripción` generado una sola vez
  (backfill) y mantenido en el repositorio. Solo contiene entradas para productos que no tenían
  descripción real al momento del backfill.
- **`scraper/generar_web.py`**: al construir cada producto, la prioridad de la descripción es:
  1. Descripción real de La Rebaja (`precios_larebaja.json`) → `funcion_fuente: "real"`.
  2. Descripción de `descripciones_ia.json` → `funcion_fuente: "ia"`.
  3. Ninguna → `funcion: null`, `funcion_fuente: null`.
- **`scraper/plantilla_web.html`**: el badge se calcula a partir de `funcion_fuente` en vez de solo
  la presencia de `funcion`:
  - `"real"` → badge **verificado**.
  - `"ia"` → badge **no verificado** (mismo texto que ya anticipa el disclaimer de la página).
  - `null` → badge **sin descripción** (comportamiento actual, sin cambios).

## 4. Proceso de backfill

1. Un script (`scraper/reportar_sin_descripcion.py`) lee `catalogo.json` + `precios_larebaja.json` +
   el `descripciones_ia.json` existente (si lo hay), y calcula qué EAN todavía no tienen ninguna
   descripción. Entrega lotes de tamaño fijo (300 productos: EAN, nombre, proveedor) en un archivo
   temporal para que Claude los redacte.
2. Claude redacta una descripción corta por producto del lote, siguiendo el estilo y las reglas de la
   sección 2.
3. El lote redactado se fusiona en `data/descripciones_ia.json` (nunca se sobreescribe una entrada ya
   existente) y se commitea. Esto hace el proceso reanudable: si se interrumpe, el siguiente lote
   retoma desde los EAN que aún faltan.
4. Se repite hasta cubrir los ~13,000 productos sin descripción. Al finalizar, se corre
   `scraper/generar_web.py` una vez más para confirmar cobertura del 100%.

## 5. Pruebas (`tests/test_pipeline.py`)

- La descripción real tiene prioridad sobre la de IA cuando ambas existen para el mismo EAN.
- Se usa la descripción de IA cuando no hay real, y el producto queda con `funcion_fuente: "ia"`.
- Sin ninguna descripción disponible, `funcion` es `null` y `funcion_fuente` es `null`.
- El badge de la plantilla refleja correctamente los tres estados (verificado / no verificado / sin
  descripción) — prueba manual visual, no automatizada (es JS embebido en el HTML).

## 6. Fuera de alcance

- Generación automática de descripciones para productos nuevos en el pipeline diario.
- Traducción o localización de descripciones.
- Verificación por un químico farmacéutico de las descripciones generadas (proceso externo al
  sistema, ya conocido y aceptado por el usuario).
