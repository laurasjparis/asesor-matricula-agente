"""Valores esperados calculados a mano desde data/*.csv (historial acortado, 23 filas)."""
from herramientas import *

r = resumen_academico()
assert r["materias_aprobadas"] == 19 and r["materias_pendientes"] == 26, r
assert r["creditos_aprobados"] == 53 and r["creditos_totales_pensum"] == 149, r
assert r["promedio_ponderado"] == 3.65, r
assert r["materias_reprobadas_sin_aprobar"] == ["CM0232", "CM0246", "DF0239"], r

assert [m["codigo"] for m in buscar_materia("Cálculo")["materias"]] == ["CM0230", "CM0231", "CM0232"]
assert buscar_materia("Termodinámica")["encontrada"] is False

v = verificar_prerrequisitos("DF0239")           # perdida (2.3) y NO vuelta a aprobar
assert v["ya_aprobada"] is False and v["puede_inscribir"] is True and v["prerrequisitos_faltantes"] == [], v
assert verificar_prerrequisitos("CM0231")["ya_aprobada"] is True   # 2.7 -> 3.0 (borde)

c = validar_carga(["PT0131", "ST0277", "ST0257"])
assert c["valida"] is False and c["creditos_totales"] == 25, c
assert len(c["problemas"]) == 2, c
assert c["problemas"][0]["codigo"] == "ST0257" and "ST0254" in c["problemas"][0]["motivo"], c
assert c["problemas"][1]["codigo"] is None and "25" in c["problemas"][1]["motivo"], c

print("✅ Todos los valores esperados coinciden")
