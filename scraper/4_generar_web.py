"""
Genera web/index.html a partir de data/muestra_productos.json.
La pagina es un archivo unico y autocontenido (HTML+CSS+JS con los datos
incrustados), para que cualquier vendedor la abra con doble clic sin
necesitar servidor ni conexion a internet.
"""
import json
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent / "data" / "muestra_productos.json"
OUT_PATH = Path(__file__).parent.parent / "web" / "index.html"

productos = json.loads(DATA_PATH.read_text(encoding="utf-8"))
productos_json = json.dumps(productos, ensure_ascii=False)

HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Consulta de Precios - Farmacia</title>
<style>
  :root {
    --verde: #1a7f37;
    --rojo: #c0392b;
    --gris-bg: #f5f6f8;
    --borde: #dfe3e8;
    --texto: #1f2430;
    --texto-suave: #5a6270;
  }
  * { box-sizing: border-box; }
  body {
    font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif;
    background: var(--gris-bg);
    color: var(--texto);
    margin: 0;
    padding: 0;
  }
  header {
    background: #ffffff;
    border-bottom: 1px solid var(--borde);
    padding: 20px 24px;
    position: sticky;
    top: 0;
    z-index: 10;
  }
  header h1 {
    margin: 0 0 12px 0;
    font-size: 1.3rem;
  }
  #buscador {
    width: 100%;
    max-width: 520px;
    padding: 10px 14px;
    font-size: 1rem;
    border: 1px solid var(--borde);
    border-radius: 8px;
  }
  main {
    padding: 20px 24px 60px;
    max-width: 1000px;
    margin: 0 auto;
  }
  .resumen {
    color: var(--texto-suave);
    font-size: 0.9rem;
    margin-bottom: 14px;
  }
  .tarjeta {
    background: #fff;
    border: 1px solid var(--borde);
    border-radius: 10px;
    padding: 16px 18px;
    margin-bottom: 12px;
  }
  .tarjeta h2 {
    font-size: 1.05rem;
    margin: 0 0 4px 0;
  }
  .proveedor {
    color: var(--texto-suave);
    font-size: 0.85rem;
    margin-bottom: 10px;
  }
  .funcion {
    font-size: 0.92rem;
    margin-bottom: 10px;
    line-height: 1.4;
  }
  .fuente {
    display: inline-block;
    font-size: 0.72rem;
    padding: 2px 8px;
    border-radius: 20px;
    margin-bottom: 10px;
  }
  .fuente.verificado {
    background: #e6f4ea;
    color: var(--verde);
  }
  .fuente.no-verificado {
    background: #fdecea;
    color: #9c4221;
  }
  .precios {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 10px;
    margin-top: 8px;
  }
  .precio-box {
    border: 1px solid var(--borde);
    border-radius: 8px;
    padding: 10px 12px;
  }
  .precio-box .nombre-tienda {
    font-size: 0.78rem;
    color: var(--texto-suave);
    margin-bottom: 2px;
  }
  .precio-box .valor {
    font-size: 1.05rem;
    font-weight: 600;
  }
  .precio-box.mi-precio {
    background: #f0f4ff;
    border-color: #b6c6f2;
  }
  .precio-box.alerta .valor {
    color: var(--rojo);
  }
  .precio-box.ok .valor {
    color: var(--verde);
  }
  .precio-box.sin-dato .valor {
    color: var(--texto-suave);
    font-weight: 400;
    font-size: 0.85rem;
  }
  .badge-alerta {
    display: inline-block;
    margin-top: 10px;
    background: #fdecea;
    color: var(--rojo);
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 0.82rem;
    font-weight: 600;
  }
  .badge-ok {
    display: inline-block;
    margin-top: 10px;
    background: #e6f4ea;
    color: var(--verde);
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 0.82rem;
    font-weight: 600;
  }
  #vacio {
    text-align: center;
    color: var(--texto-suave);
    padding: 40px 0;
  }
  footer {
    text-align: center;
    color: var(--texto-suave);
    font-size: 0.78rem;
    padding: 20px;
  }
</style>
</head>
<body>

<header>
  <h1>Consulta de precios y función de medicamentos</h1>
  <input type="text" id="buscador" placeholder="Buscar medicamento o producto por nombre...">
</header>

<main>
  <div class="resumen" id="resumen"></div>
  <div id="lista"></div>
  <div id="vacio" style="display:none;">No se encontraron productos. Prueba con otra palabra clave.</div>
</main>

<footer>
  Muestra de prueba: __TOTAL__ productos. Los precios de la competencia se actualizan periódicamente.
  Las descripciones marcadas como "no verificado" fueron generadas automáticamente y deben ser
  confirmadas por el químico farmacéutico antes de usarse como asesoría clínica.
</footer>

<script>
const PRODUCTOS = __PRODUCTOS_JSON__;

const fmt = (n) => n == null ? null : '$' + Math.round(n).toLocaleString('es-CO');

function precioBox(nombreTienda, valor, precioReferencia) {
  if (valor == null) {
    return `<div class="precio-box sin-dato">
      <div class="nombre-tienda">${nombreTienda}</div>
      <div class="valor">Sin dato aún</div>
    </div>`;
  }
  let clase = '';
  if (precioReferencia != null) {
    clase = valor < precioReferencia ? 'alerta' : (valor > precioReferencia ? 'ok' : '');
  }
  return `<div class="precio-box ${clase}">
    <div class="nombre-tienda">${nombreTienda}</div>
    <div class="valor">${fmt(valor)}</div>
  </div>`;
}

function renderProducto(p) {
  const comp = p.precios_competencia || {};
  const fuenteClase = p.funcion_fuente === 'drogueria_competencia' ? 'verificado' : 'no-verificado';
  const fuenteTexto = p.funcion_fuente === 'drogueria_competencia'
    ? 'Fuente: ficha de droguería de la competencia'
    : '⚠ Generado automáticamente - no verificado, confirmar con el químico farmacéutico';

  // Alerta si vendemos mas barato que la competencia (precio de venta real menor)
  const preciosCompetenciaDisponibles = Object.values(comp).filter(v => v != null);
  const minCompetencia = preciosCompetenciaDisponibles.length ? Math.min(...preciosCompetenciaDisponibles) : null;
  let badge = '';
  if (minCompetencia != null) {
    if (p.precio_farmacia < minCompetencia) {
      badge = `<span class="badge-alerta">Estás vendiendo más barato que la competencia (diferencia: ${fmt(minCompetencia - p.precio_farmacia)})</span>`;
    } else {
      badge = `<span class="badge-ok">Tu precio está igual o por encima de la competencia</span>`;
    }
  }

  return `
  <div class="tarjeta">
    <h2>${p.nombre}</h2>
    <div class="proveedor">Proveedor: ${p.proveedor} · EAN: ${p.ean}</div>
    <div class="funcion">${p.funcion}</div>
    <span class="fuente ${fuenteClase}">${fuenteTexto}</span>
    <div class="precios">
      ${precioBox('Tu precio', p.precio_farmacia, null).replace('precio-box', 'precio-box mi-precio')}
      ${precioBox('Cruz Verde', comp.cruz_verde, p.precio_farmacia)}
      ${precioBox('La Rebaja', comp.la_rebaja, p.precio_farmacia)}
      ${precioBox('Farmatodo', comp.farmatodo, p.precio_farmacia)}
    </div>
    ${badge}
  </div>`;
}

function render(lista) {
  const cont = document.getElementById('lista');
  const vacio = document.getElementById('vacio');
  document.getElementById('resumen').textContent =
    `Mostrando ${lista.length} de ${PRODUCTOS.length} productos.`;
  if (lista.length === 0) {
    cont.innerHTML = '';
    vacio.style.display = 'block';
    return;
  }
  vacio.style.display = 'none';
  cont.innerHTML = lista.map(renderProducto).join('');
}

document.getElementById('buscador').addEventListener('input', (e) => {
  const q = e.target.value.trim().toLowerCase();
  if (!q) { render(PRODUCTOS); return; }
  const filtrados = PRODUCTOS.filter(p =>
    p.nombre.toLowerCase().includes(q) || p.proveedor.toLowerCase().includes(q)
  );
  render(filtrados);
});

render(PRODUCTOS);
</script>

</body>
</html>
"""

html_final = HTML.replace("__PRODUCTOS_JSON__", productos_json).replace("__TOTAL__", str(len(productos)))
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
OUT_PATH.write_text(html_final, encoding="utf-8")
print(f"Web generada -> {OUT_PATH}")
