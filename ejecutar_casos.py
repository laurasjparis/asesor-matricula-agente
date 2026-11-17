"""
ejecutar_casos.py — Corre los 5 casos de prueba con el agente y guarda la traza.

Uso:
    python ejecutar_casos.py            # corre los 5 casos
    python ejecutar_casos.py 3 5        # solo los casos 3 y 5

Genera resultados_casos.json (herramienta, argumentos, resultado y respuesta
final de cada caso) para pegar en el README.
Si corres solo algunos casos, NO sobrescribe resultados_casos.json: guarda en
resultados_parcial_<casos>_<hora>.json para que no se pierda la corrida completa.

Las columnas "esperado_*" se calcularon a mano desde los CSV ANTES de correr.
Las verificaciones automáticas son solo una ayuda: el veredicto final lo da
una persona leyendo la respuesta.
"""

import json
import sys
import unicodedata
from datetime import datetime

from agente import run_agent


def _n(texto: str) -> str:
    """Minúsculas y sin tildes, para comparar texto."""
    t = unicodedata.normalize("NFD", texto)
    return "".join(c for c in t if unicodedata.category(c) != "Mn").lower()


CASOS = [
    {
        "id": 1, "nombre": "Consulta ambigua",
        "pregunta": "¿Puedo ver Cálculo?",
        "presupuesto": 5,
        "esperado_herramientas": ["buscar_materia"],
        "debe_contener": ["CM0230", "CM0231", "CM0232"],
        "no_debe_contener": [],
        "esperado": "Lista Cálculo I, II y III y pide aclarar cuál.",
    },
    {
        "id": 2, "nombre": "Materia inexistente",
        "pregunta": "¿Puedo inscribir Termodinámica?",
        "presupuesto": 5,
        "esperado_herramientas": ["buscar_materia"],
        "debe_contener": [],
        "no_debe_contener": [],
        "esperado": "Dice que no existe en el pensum; no inventa datos.",
    },
    {
        "id": 3, "nombre": "Materia perdida sin aprobar",
        "pregunta": "Perdí Física II la primera vez, ¿ya la tengo aprobada?",
        "presupuesto": 5,
        "esperado_herramientas": ["buscar_materia", "verificar_prerrequisitos"],
        "debe_contener": [],
        "no_debe_contener": ["2.3"],          # las herramientas no devuelven notas
        "esperado": ("DF0239 NO está aprobada (solo tiene un 2.3). Puede inscribirla: "
                     "su prerrequisito DF0236 está cumplido. No cita notas."),
    },
    {
        "id": 4, "nombre": "Carga inválida",
        "pregunta": ("Quiero inscribir Período de Práctica, Gestión de Proyectos "
                     "y Sistemas Operativos. ¿Puedo?"),
        "presupuesto": 5,
        "esperado_herramientas": ["buscar_materia", "validar_carga"],
        "debe_contener": ["25", "21", "ST0254"],
        "no_debe_contener": [],
        "esperado": ("valida=False, 25 créditos (18+3+4). ST0257 falla por prerrequisito "
                     "ST0254; excede 21. ST0277 y PT0131 sin problema propio."),
    },
    {
        "id": 5, "nombre": "Presupuesto agotado",
        "pregunta": "Dame mi promedio, cuántos créditos me faltan y si ya aprobé Física II.",
        "presupuesto": 1,
        "esperado_herramientas": [],           # solo se ejecuta 1 llamada
        "debe_contener": [],
        "no_debe_contener": [],
        "esperado": ("Solo 1 tool call ejecutada. Si fue resumen_academico: promedio 3.65, "
                     "53 de 149 créditos aprobados (faltan 96). Avisa que no verificó Física II "
                     "y que el motivo es el límite de consultas."),
    },
]


def verificar(caso: dict, respuesta: str, traza: list) -> list:
    """Devuelve una lista de avisos (vacía = sin observaciones automáticas)."""
    avisos = []
    usadas = {p["herramienta"] for p in traza}

    for h in caso["esperado_herramientas"]:
        if h not in usadas:
            avisos.append(f"no llamó a la herramienta esperada: {h}")
    if len(traza) > caso["presupuesto"]:
        avisos.append(f"superó el presupuesto ({len(traza)} > {caso['presupuesto']})")
    for s in caso["debe_contener"]:
        if _n(s) not in _n(respuesta):
            avisos.append(f"la respuesta no menciona '{s}'")
    for s in caso["no_debe_contener"]:
        if _n(s) in _n(respuesta):
            avisos.append(f"la respuesta menciona '{s}' (posible dato inventado)")
    return avisos


def main():
    ids = {int(a) for a in sys.argv[1:]} or {c["id"] for c in CASOS}
    resultados = []

    for caso in CASOS:
        if caso["id"] not in ids:
            continue
        print(f"\n{'═' * 70}\nCASO {caso['id']}: {caso['nombre']}\n{'═' * 70}")
        print(f"Esperado (a mano): {caso['esperado']}")

        try:
            respuesta, traza = run_agent(caso["pregunta"],
                                         max_tool_calls=caso["presupuesto"])
            error = None
        except Exception as e:                      # no perder los demás casos
            respuesta, traza, error = "", [], f"{type(e).__name__}: {e}"
            print(f"❌ El caso falló al ejecutarse: {error}")

        avisos = verificar(caso, respuesta, traza) if not error else ["error de ejecución"]
        print(f"\nTool calls: {len(traza)}")
        for i, p in enumerate(traza, 1):
            print(f"  [{i}] {p['herramienta']}({json.dumps(p['argumentos'], ensure_ascii=False)})")
        print("Verificación automática:", "sin observaciones ✅" if not avisos else avisos)

        resultados.append({
            "caso": caso["id"], "nombre": caso["nombre"],
            "pregunta": caso["pregunta"], "presupuesto": caso["presupuesto"],
            "esperado": caso["esperado"],
            "traza": traza, "respuesta_final": respuesta,
            "avisos_automaticos": avisos, "error": error,
        })

    if ids == {c["id"] for c in CASOS}:
        salida = "resultados_casos.json"
    else:
        salida = (f"resultados_parcial_{'-'.join(map(str, sorted(ids)))}_"
                  f"{datetime.now():%H%M%S}.json")
    with open(salida, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
    print(f"\n💾 Guardado en {salida}")


if __name__ == "__main__":
    main()
