# Diseño: Sistema de comparación de precios vs. La Rebaja (catálogo completo, 3 sedes)

Fecha: 2026-07-05

## 1. Contexto

El proyecto ya tiene un prototipo funcional (`scraper/1_extraer_muestra.py` a `4_generar_web.py`) que:
toma una muestra de 150 productos, consulta precios en la API pública de Drogas La Rebaja, fusiona
descripciones (reales o generadas por IA) y genera una página HTML estática autocontenida.

Este diseño define cómo escalar ese prototipo a producción real para las 3 droguerías del negocio.

## 2. Objetivo y requisitos confirmados

- **Uso:** consulta en el punto de venta — el vendedor compara su precio contra La Rebaja al momento
  de atender al cliente.
- **Comparación:** solo contra Drogas La Rebaja (no se implementan Cruz Verde ni Farmatodo).
- **Alcance:** catálogo completo, **16,810 productos** (no una muestra).
- **Frecuencia:** actualización diaria.
- **Sedes:** 3 droguerías, cada una con un computador de punto de venta. Comparten **el mismo
  catálogo y los mismos precios** (no hay catálogos independientes por sede).
- **Distribución:** página alojada en internet; cada sede abre la misma URL fija.
- **Privacidad:** el contenido puede ser público (repositorio y sitio públicos son aceptables).
- **Origen de datos propios:** `productos.xls` se reexporta a diario en el computador local, en una
  ruta fija. Contiene columnas `Proveedor`, `Denominación`, `Venta Real` (precio de venta propio) y
  `EAN`.
- **Origen de datos de ventas (rotación):** archivo de facturación histórico (`asdasdas.xlsx`,
  ejemplo real usado para validar el diseño), con una fila por venta individual, columnas incluyendo
  `Codigo Producto`, `Nombre Producto`, `Cantidad Caja/Blister/Unidad`, `Valor Caja/Blister/Unidad`,
  `Fecha`. No comparte EAN ni código con el catálogo — el cruce se hace por nombre normalizado.

## 3. Arquitectura general

```
[Computador local, 1 sede]                [GitHub (nube)]
  productos.xls (se reexporta          →  Actions workflow diario (cron fijo)
  a diario) ────────────────┐             ├─ 1. Selecciona lote del día
                              │             │   (top-ventas + franja rotativa)
  script local (rápido,       │             ├─ 2. Scraping vs La Rebaja (ese lote)
  segundos):                  │             ├─ 3. Fusiona descripciones
  - lee Excel                 │             ├─ 4. Regenera datos.json + index.html
  - normaliza catálogo        │             └─ 5. Publica en GitHub Pages
  - sube data/catalogo.json ──┘                    │
    a GitHub (git push)                             ▼
                                    3 droguerías abren la MISMA URL fija
                                    en su computador de punto de venta
```

**Decisiones clave:**
- El paso local es minúsculo (segundos): solo lee el Excel y sube el catálogo normalizado a git. No
  requiere que el computador quede encendido de madrugada.
- Todo el trabajo pesado (scraping, fusión, generación, publicación) corre en GitHub Actions, gratis
  e ilimitado por tratarse de un repositorio público.
- El workflow en la nube corre en un **horario fijo diario** (ej. 3:00 AM) sin depender de que el
  paso local se haya ejecutado ese día — si el catálogo propio no se actualizó, el scraping de
  precios de competencia continúa igual con el catálogo más reciente disponible.

## 4. Cruce de datos de ventas (ranking de popularidad)

Se probó el cruce real entre `productos.xls` (16,810 productos) y el archivo de ventas
(102,176 filas, 3,432 productos únicos vendidos entre enero y junio 2026):

- **Cruce exacto por nombre normalizado** (mayúsculas, sin tildes, sin puntuación): 2,773 de 3,432
  productos vendidos (**80.8%**) coinciden exactamente con una fila del catálogo.
- Se probó fuzzy matching para rescatar el resto y se descartó: produjo coincidencias incorrectas y
  potencialmente peligrosas (ej. emparejó un catéter calibre 24G con uno de 22G; Coca-Cola 600ml con
  Bio Oil 60ml).
- **Decisión:** usar únicamente el cruce exacto por nombre normalizado. Los productos vendidos sin
  coincidencia exacta, y los productos sin ninguna venta registrada en el periodo, se tratan como
  "sin dato de ventas" y caen en la rotación pareja (sección 5), sin forzar un cruce dudoso.
- **Métrica de ranking:** suma de unidades vendidas (`Cantidad Caja + Cantidad Blister + Cantidad
  Unidad`) por producto en el periodo disponible.

## 5. Lógica de priorización y rotación de lotes

Para evitar que el scraping diario tome ~2.8 horas (16,810 productos a 0.6s cada uno), se divide el
catálogo en:

1. **Tier "siempre" (~1,500 productos):** los más vendidos según el ranking de la sección 4. Se
   actualizan **todos los días**, sin excepción.
2. **Tier "rotación" (~15,310 productos restantes):** productos sin dato de ventas confiable o fuera
   del top 1,500. Se dividen en **7 franjas fijas y deterministas** (ej. `hash(EAN) % 7`), una por
   día de la semana. Cada producto cae siempre en el mismo día de la semana — no se necesita guardar
   un cursor de estado entre ejecuciones, lo que hace el sistema auto-corregible si algún día se
   salta una ejecución.
3. **Presupuesto diario resultante:** ~1,500 (fijo) + ~2,187 (una franja de 15,310/7) ≈ **3,687
   productos/día**, dentro del objetivo de ~4,000/día. Cobertura completa del catálogo cada 7 días.
4. La web muestra la fecha del último precio de competencia consultado por producto, ya que no todos
   se refrescan el mismo día.

## 6. Manejo de errores y confiabilidad

- **Errores por producto:** reintento con espera progresiva (2 intentos) ante fallos de red; si
  persiste, se conserva el último precio conocido (nunca se sobreescribe con `null`) y se registra
  en el log de la ejecución.
- **Escrituras atómicas:** los archivos de datos se escriben a un temporal y se reemplazan al
  finalizar, para no dejar el catálogo corrupto ante un corte a mitad de proceso.
- **Resiliencia del pipeline:** el workflow en la nube corre siempre a su hora fija, incluso si el
  paso local no subió catálogo nuevo ese día.
- **Protección contra publicaciones rotas:** antes de publicar, se compara la tasa de coincidencia
  con La Rebaja del día contra la del día anterior; si cae drásticamente (señal de que la API cambió
  o está bloqueada), se aborta la publicación de ese día y se conserva la última versión buena
  conocida.
- **Notificaciones:** se usa el aviso por correo nativo de GitHub Actions ante fallos de un workflow
  programado — sin integraciones adicionales.
- **Registro:** cada ejecución deja un resumen (productos actualizados, fallidos, sin match,
  duración) visible en el historial de GitHub Actions.

## 7. Diseño de la web (frontend)

El HTML actual embebe todos los datos como JSON dentro del propio archivo (65KB para 150 productos).
Con 16,810 productos eso serían ~7MB en un solo archivo y renderizar todas las tarjetas en el DOM de
una vez sería lento en un computador de punto de venta.

- **Separar datos de la página:** `index.html` liviano (buscador + lógica) que descarga
  `datos.json` aparte una sola vez al abrir la página.
- **Buscar en memoria, renderizar poco:** el filtrado ocurre sobre los 16,810 productos en memoria
  (rápido), pero solo se muestran los primeros ~50 resultados coincidentes, con indicación de
  "mostrando 50 de N resultados, afina tu búsqueda".
- **Sin listado inicial:** la página pide escribir un término de búsqueda antes de mostrar
  resultados, en vez de listar el catálogo completo al cargar.
- **Evitar caché vieja:** `datos.json` se referencia con una marca de versión/fecha en la URL para
  que el navegador siempre traiga la versión más reciente tras cada publicación.
- Se conserva el resaltado visual (verde/rojo si el precio propio es menor/mayor que La Rebaja) y se
  añade la fecha del último precio de competencia consultado por producto.

## 8. Componentes y estructura de archivos (resultado esperado)

```
farmacia-web/
├── .github/workflows/actualizar.yml   # workflow diario (scraping + publicación)
├── scraper/
│   ├── extraer_catalogo.py            # lee productos.xls, normaliza, sube a git (local)
│   ├── calcular_ranking_ventas.py     # cruce exacto por nombre + ranking de unidades vendidas
│   ├── seleccionar_lote.py            # decide tier "siempre" + franja rotativa del día
│   ├── scrapear_larebaja.py           # consulta API La Rebaja solo para el lote del día
│   ├── fusionar_funcion.py            # descripciones reales / IA (ya existe, se reutiliza)
│   ├── generar_web.py                 # genera index.html + datos.json
│   └── config.py                      # rutas y parámetros (ruta Excel, tamaños de lote, etc.)
├── data/
│   ├── catalogo.json                  # catálogo maestro (subido por el paso local)
│   ├── precios_larebaja.json          # caché acumulado de precios + fecha de última consulta
│   └── ranking_ventas.json            # ranking de unidades vendidas por producto
├── web/
│   ├── index.html
│   └── datos.json
├── requirements.txt
└── README.md
```

## 9. Pruebas

- **Cruce de nombres:** prueba automatizada que verifica la tasa de coincidencia exacta sobre una
  muestra fija y alerta si cae por debajo de un umbral (regresión si cambia el formato del Excel).
- **Lógica de lotes:** prueba que confirma que cada producto cae en exactamente una franja de las 7,
  que el tier "siempre" nunca se duplica dentro de una franja, y que en 7 días se cubre el 100% del
  catálogo.
- **Fusión de precios:** prueba que confirma que un producto no tocado en el lote del día conserva su
  precio y fecha anteriores (no se borra ni se pone en `null`).
- **Manejo de errores:** prueba que simula fallos de red y confirma que se aplican los reintentos y
  que el precio anterior se conserva tras agotar los intentos.
- **Validación pre-publicación:** prueba que confirma que una caída drástica en la tasa de match
  aborta la publicación y conserva la versión anterior.
- **Verificación manual inicial:** antes de activar el catálogo completo en producción, correr el
  pipeline completo una vez sobre el catálogo real y revisar manualmente una muestra de resultados
  antes de dejarlo en automático.
