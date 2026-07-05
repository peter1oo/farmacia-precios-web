"""
Valida que la tasa de match de hoy contra La Rebaja no haya caido de forma
drastica frente al historial reciente (ver seccion 6 del diseno). Una caida
grande suele significar que la API cambio o esta bloqueando las consultas,
no que la competencia dejo de vender productos de un dia para otro -- en
ese caso es mejor no publicar y conservar la ultima version buena conocida.
"""
import config


def debe_publicar(historial_tasa_match: list) -> tuple:
    """Devuelve (True/False, motivo). Necesita al menos 2 entradas de
    historial (hoy + al menos una anterior) para poder comparar; si no hay
    suficiente historial, deja pasar (no hay con que comparar todavia)."""
    if len(historial_tasa_match) < 2:
        return True, "sin historial suficiente para comparar, se publica"

    tasa_hoy = historial_tasa_match[-1]["tasa_match"]
    anteriores = [h["tasa_match"] for h in historial_tasa_match[:-1]]
    promedio_anterior = sum(anteriores) / len(anteriores)

    if promedio_anterior == 0:
        return True, "promedio anterior era 0, no hay base para detectar caida"

    if tasa_hoy < promedio_anterior * config.UMBRAL_CAIDA_MATCH:
        motivo = (
            f"tasa de hoy ({tasa_hoy:.1%}) cayo por debajo del "
            f"{config.UMBRAL_CAIDA_MATCH:.0%} del promedio reciente ({promedio_anterior:.1%})"
        )
        return False, motivo

    return True, f"tasa de hoy ({tasa_hoy:.1%}) dentro de lo normal (promedio: {promedio_anterior:.1%})"
