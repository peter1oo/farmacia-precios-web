from datetime import date

from calcular_ranking_ventas import normalizar
from extraer_catalogo import PATRON_PROMOCIONAL
from generar_web import resolver_funcion
from scrapear_larebaja import construir_consulta_texto, fusionar_resultado
from seleccionar_lote import franja_de, seleccionar
from validar_publicacion import debe_publicar


# --- normalizar (cruce de nombres, seccion 4) ---

def test_normalizar_ignora_tildes_mayusculas_y_puntuacion():
    assert normalizar("Línea de Cuidado 100% Natural") == normalizar("LINEA DE CUIDADO 100 NATURAL")


def test_normalizar_es_estable_para_texto_ya_normalizado():
    assert normalizar("ACETAMINOFEN 500 MG") == "ACETAMINOFEN 500 MG"


def test_normalizar_colapsa_espacios_repetidos():
    assert normalizar("PANTENE   KERATINA") == "PANTENE KERATINA"


# --- filtro de productos promocionales (seccion 4, limpieza de catalogo) ---

def test_patron_promocional_detecta_obsequios_y_kits_virtuales():
    for nombre in [
        "OBS. KIT POP SEPARATA TU DROGUERIA MAY",
        "OBSEQUIO HALEON MORRAL TOTTO",
        "KIT VIRT HALEON COM2 GTS SET TOALLAS OEK",
    ]:
        assert PATRON_PROMOCIONAL.search(nombre), f"deberia detectar: {nombre}"


def test_patron_promocional_no_descarta_productos_reales():
    for nombre in ["BRONCHO-VAXOM ADULTO 10 CAP", "ACETAMINOFEN 500MG X 20 TAB", "KIT DE INYECTOLOGIA MEDISPO"]:
        assert not PATRON_PROMOCIONAL.search(nombre), f"no deberia descartar: {nombre}"


# --- franja_de / seleccionar (seccion 5, rotacion de lotes) ---

def test_franja_de_es_deterministica():
    assert franja_de("7704403005107") == franja_de("7704403005107")


def test_franja_de_cae_dentro_del_rango():
    for ean in ["1", "123456789", "7704403005107", "abc"]:
        assert 0 <= franja_de(ean, num_franjas=7) < 7


def _catalogo_sintetico(n=700):
    return [{"ean": str(1_000_000 + i), "nombre": f"PRODUCTO {i}", "proveedor": "X"} for i in range(n)]


def test_seleccionar_top_siempre_se_repite_todos_los_dias():
    catalogo = _catalogo_sintetico(200)
    ranking = [{"ean": p["ean"], "unidades_vendidas": 200 - i} for i, p in enumerate(catalogo[:50])]

    lote_lunes = seleccionar(catalogo, ranking, date(2026, 7, 6))
    lote_martes = seleccionar(catalogo, ranking, date(2026, 7, 7))

    top_lunes = set(lote_lunes["eans_a_scrapear"]) & {r["ean"] for r in ranking}
    top_martes = set(lote_martes["eans_a_scrapear"]) & {r["ean"] for r in ranking}
    assert top_lunes == top_martes == {r["ean"] for r in ranking}


def test_seleccionar_las_7_franjas_cubren_todo_sin_solapar():
    catalogo = _catalogo_sintetico(700)
    ranking = [{"ean": p["ean"], "unidades_vendidas": 700 - i} for i, p in enumerate(catalogo[:100])]
    eans_top_siempre = {r["ean"] for r in ranking[:100]}

    dias = [date(2026, 7, 6 + i) for i in range(7)]  # un lunes a un domingo
    franjas = [set(seleccionar(catalogo, ranking, d)["eans_a_scrapear"]) - eans_top_siempre for d in dias]

    union = set().union(*franjas)
    esperado = {p["ean"] for p in catalogo} - eans_top_siempre
    assert union == esperado, "las 7 franjas deben cubrir exactamente el resto del catalogo"

    for i in range(7):
        for j in range(i + 1, 7):
            assert not (franjas[i] & franjas[j]), "las franjas no deben solaparse"


# --- construir_consulta_texto (el sitio rechaza el "+" literal, con o sin URL-encode) ---

def test_construir_consulta_texto_quita_el_signo_mas():
    assert "+" not in construir_consulta_texto("VITAMINA E 400 UI+A")


def test_construir_consulta_texto_limita_a_4_palabras():
    assert construir_consulta_texto("uno dos tres cuatro cinco seis") == "uno dos tres cuatro"


# --- fusionar_resultado (seccion 6, no perder datos ante fallas) ---

def test_fusionar_resultado_actualiza_cuando_hay_precio():
    entrada = fusionar_resultado({}, 1000.0, {"descripcion": "desc"}, "ean", "2026-07-05")
    assert entrada["precio"] == 1000.0
    assert entrada["disponible"] is True
    assert entrada["descripcion"] == "desc"


def test_fusionar_resultado_sin_match_no_borra_precio_anterior():
    anterior = {"precio": 5000.0, "descripcion": "desc vieja", "ultima_consulta": "2026-07-01"}
    entrada = fusionar_resultado(anterior, None, None, None, "2026-07-05")
    assert entrada["precio"] == 5000.0, "el precio anterior no debe borrarse si hoy no hubo match"
    assert entrada["descripcion"] == "desc vieja"
    assert entrada["disponible"] is False
    assert entrada["ultima_consulta"] == "2026-07-05"


# --- resolver_funcion (descripciones IA, ver diseno 2026-07-06) ---

def test_resolver_funcion_prioriza_descripcion_real_sobre_ia():
    funcion, fuente = resolver_funcion({"descripcion": "real"}, "generada por ia")
    assert (funcion, fuente) == ("real", "real")


def test_resolver_funcion_usa_ia_si_no_hay_real():
    funcion, fuente = resolver_funcion({}, "generada por ia")
    assert (funcion, fuente) == ("generada por ia", "ia")


def test_resolver_funcion_ninguna_disponible():
    assert resolver_funcion({}, None) == (None, None)


# --- validar_publicacion (seccion 6, no publicar ante caida sospechosa) ---

def test_debe_publicar_sin_historial_suficiente():
    ok, _ = debe_publicar([{"tasa_match": 0.2}])
    assert ok is True


def test_debe_publicar_aborta_si_cae_drasticamente():
    historial = [{"tasa_match": 0.8}, {"tasa_match": 0.75}, {"tasa_match": 0.05}]
    ok, motivo = debe_publicar(historial)
    assert ok is False
    assert "cayo" in motivo


def test_debe_publicar_permite_variacion_normal():
    historial = [{"tasa_match": 0.8}, {"tasa_match": 0.75}, {"tasa_match": 0.7}]
    ok, _ = debe_publicar(historial)
    assert ok is True
