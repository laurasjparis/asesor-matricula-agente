"""
herramientas_stub.py — Versión FALSA de herramientas.py para probar el agente.

Usa datos inventados en memoria (no lee los CSV) pero devuelve EXACTAMENTE
las mismas estructuras definidas en CONTRATO_HERRAMIENTAS.md.

Cuando exista herramientas.py (la versión real que lee data/*.csv),
agente.py la usa automáticamente y este archivo deja de usarse.
"""

import unicodedata

NOTA_MINIMA_APROBACION = 3.0
NOTA_MAXIMA = 5.0
MAX_CREDITOS_SEMESTRE = 21


# ════════════════════════════════════════════════════════════
#  DATOS FALSOS — misma forma que data/pensum.csv y data/historial.csv
# ════════════════════════════════════════════════════════════

PENSUM = [
    # codigo,  nombre,                               creditos, semestre, prerrequisitos
    {"codigo": "MAT101", "nombre": "Cálculo I",                       "creditos": 4, "semestre": 1, "prerrequisitos": []},
    {"codigo": "PRG101", "nombre": "Introducción a la Programación",  "creditos": 3, "semestre": 1, "prerrequisitos": []},
    {"codigo": "QUI101", "nombre": "Química General",                 "creditos": 3, "semestre": 1, "prerrequisitos": []},
    {"codigo": "MAT102", "nombre": "Cálculo II",                      "creditos": 4, "semestre": 2, "prerrequisitos": ["MAT101"]},
    {"codigo": "PRG102", "nombre": "Programación Orientada a Objetos","creditos": 3, "semestre": 2, "prerrequisitos": ["PRG101"]},
    {"codigo": "MAT110", "nombre": "Álgebra Lineal",                  "creditos": 3, "semestre": 2, "prerrequisitos": ["MAT101"]},
    {"codigo": "MAT201", "nombre": "Cálculo III",                     "creditos": 4, "semestre": 3, "prerrequisitos": ["MAT102"]},
    {"codigo": "FIS201", "nombre": "Física Mecánica",                 "creditos": 4, "semestre": 3, "prerrequisitos": ["MAT101", "MAT102"]},
    {"codigo": "PRG201", "nombre": "Estructuras de Datos",            "creditos": 3, "semestre": 3, "prerrequisitos": ["PRG102"]},
    {"codigo": "EST201", "nombre": "Probabilidad y Estadística",      "creditos": 3, "semestre": 3, "prerrequisitos": ["MAT102"]},
    {"codigo": "PRG301", "nombre": "Bases de Datos",                  "creditos": 3, "semestre": 4, "prerrequisitos": ["PRG201"]},
    {"codigo": "IA301",  "nombre": "Introducción a la IA",            "creditos": 3, "semestre": 4, "prerrequisitos": ["PRG201", "EST201"]},
]

HISTORIAL = [
    # MAT102 aparece dos veces: la perdió en 2025-2 y la aprobó en 2026-1.
    # QUI101 está perdida y no la ha vuelto a ver.
    {"codigo": "MAT101", "nota": 3.8, "periodo": "2025-1"},
    {"codigo": "PRG101", "nota": 4.2, "periodo": "2025-1"},
    {"codigo": "QUI101", "nota": 2.4, "periodo": "2025-1"},
    {"codigo": "MAT102", "nota": 2.5, "periodo": "2025-2"},
    {"codigo": "PRG102", "nota": 4.0, "periodo": "2025-2"},
    {"codigo": "MAT110", "nota": 3.1, "periodo": "2025-2"},
    {"codigo": "MAT102", "nota": 3.4, "periodo": "2026-1"},
]


# ════════════════════════════════════════════════════════════
#  FUNCIONES AUXILIARES
# ════════════════════════════════════════════════════════════

def _normalizar(texto: str) -> str:
    """Quita tildes y pasa a minúsculas: 'Cálculo' -> 'calculo'."""
    sin_tildes = unicodedata.normalize("NFD", str(texto))
    sin_tildes = "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn")
    return sin_tildes.lower().strip()


def _materia_por_codigo(codigo: str):
    """Devuelve la materia del pensum con ese código, o None si no existe."""
    codigo = str(codigo).upper().strip()
    for materia in PENSUM:
        if materia["codigo"] == codigo:
            return materia
    return None


def _codigos_aprobados() -> set:
    """Una materia está aprobada si ALGUNA de sus notas es >= 3.0."""
    return {fila["codigo"] for fila in HISTORIAL if fila["nota"] >= NOTA_MINIMA_APROBACION}


# ════════════════════════════════════════════════════════════
#  HERRAMIENTAS (las 5 del contrato)
# ════════════════════════════════════════════════════════════

def buscar_materia(nombre_o_codigo: str) -> dict:
    """Busca por código exacto o por parte del nombre (sin tildes ni mayúsculas)."""
    consulta = _normalizar(nombre_o_codigo)
    if not consulta:
        return {"encontrada": False, "mensaje": "La búsqueda está vacía."}

    # 1. Código exacto
    materia = _materia_por_codigo(consulta)
    if materia:
        return {"encontrada": True, "materias": [materia]}

    # 2. Parte del nombre (puede devolver varias → el agente pide aclarar)
    coincidencias = [m for m in PENSUM if consulta in _normalizar(m["nombre"])]
    if coincidencias:
        return {"encontrada": True, "materias": coincidencias}

    return {"encontrada": False,
            "mensaje": f"No hay materias que coincidan con '{nombre_o_codigo}'."}


def verificar_prerrequisitos(codigo: str) -> dict:
    """Indica si el estudiante cumple los prerrequisitos de una materia."""
    materia = _materia_por_codigo(codigo)
    if materia is None:
        return {"error": f"La materia '{codigo}' no existe en el pensum."}

    aprobadas = _codigos_aprobados()
    cumplidos = [p for p in materia["prerrequisitos"] if p in aprobadas]
    faltantes = [p for p in materia["prerrequisitos"] if p not in aprobadas]
    ya_aprobada = materia["codigo"] in aprobadas

    return {
        "codigo": materia["codigo"],
        "nombre": materia["nombre"],
        "ya_aprobada": ya_aprobada,
        "prerrequisitos_cumplidos": cumplidos,
        "prerrequisitos_faltantes": faltantes,
        "puede_inscribir": (not ya_aprobada) and not faltantes,
    }


def materias_disponibles(semestre: int | None = None) -> dict:
    """Materias no aprobadas con todos sus prerrequisitos aprobados."""
    if semestre is not None:
        try:
            semestre = int(semestre)   # por si el modelo lo manda como "3"
        except (TypeError, ValueError):
            return {"error": f"El semestre debe ser un número entero, llegó '{semestre}'."}

    aprobadas = _codigos_aprobados()
    disponibles = []
    for m in PENSUM:
        if m["codigo"] in aprobadas:
            continue
        if not all(p in aprobadas for p in m["prerrequisitos"]):
            continue
        if semestre is not None and m["semestre"] != semestre:
            continue
        disponibles.append({"codigo": m["codigo"], "nombre": m["nombre"],
                            "creditos": m["creditos"], "semestre": m["semestre"]})

    return {"semestre": semestre, "total": len(disponibles), "materias": disponibles}


def resumen_academico() -> dict:
    """Resumen del avance: aprobadas, créditos y promedio ponderado."""
    aprobadas = _codigos_aprobados()
    creditos_de = {m["codigo"]: m["creditos"] for m in PENSUM}

    # Promedio ponderado por créditos con TODAS las notas (incluye perdidas)
    suma = sum(fila["nota"] * creditos_de[fila["codigo"]] for fila in HISTORIAL)
    total_creditos_cursados = sum(creditos_de[fila["codigo"]] for fila in HISTORIAL)
    promedio = round(suma / total_creditos_cursados, 2) if total_creditos_cursados else 0.0

    cursadas = {fila["codigo"] for fila in HISTORIAL}
    return {
        "materias_aprobadas": len(aprobadas),
        "materias_pendientes": len(PENSUM) - len(aprobadas),
        "creditos_aprobados": sum(creditos_de[c] for c in aprobadas),
        "creditos_totales_pensum": sum(creditos_de.values()),
        "promedio_ponderado": promedio,
        "materias_reprobadas_sin_aprobar": sorted(cursadas - aprobadas),
    }


def validar_carga(codigos: list[str]) -> dict:
    """Revisa si un conjunto de materias se puede inscribir junto en un semestre."""
    if not isinstance(codigos, list):
        return {"error": "codigos debe ser una lista, ej: ['MAT201', 'FIS201']."}

    aprobadas = _codigos_aprobados()
    problemas = []
    vistos = set()
    creditos_totales = 0

    for codigo in codigos:
        codigo = str(codigo).upper().strip()
        materia = _materia_por_codigo(codigo)

        if materia is None:
            problemas.append({"codigo": codigo, "motivo": "No existe en el pensum."})
            continue                                  # no suma créditos
        if codigo in vistos:
            problemas.append({"codigo": codigo, "motivo": "Código repetido."})
            continue                                  # no suma dos veces
        vistos.add(codigo)
        creditos_totales += materia["creditos"]

        if codigo in aprobadas:
            problemas.append({"codigo": codigo, "motivo": "Ya está aprobada."})
        faltantes = [p for p in materia["prerrequisitos"] if p not in aprobadas]
        if faltantes:
            problemas.append({"codigo": codigo,
                              "motivo": f"Faltan prerrequisitos: {', '.join(faltantes)}"})

    if creditos_totales > MAX_CREDITOS_SEMESTRE:
        problemas.append({"codigo": None,
                          "motivo": f"Excede el máximo de {MAX_CREDITOS_SEMESTRE} créditos ({creditos_totales})."})

    return {
        "valida": not problemas,
        "creditos_totales": creditos_totales,
        "max_creditos": MAX_CREDITOS_SEMESTRE,
        "problemas": problemas,
    }
