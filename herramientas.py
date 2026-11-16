"""
herramientas.py — Versión REAL de las herramientas del asesor de matrícula.

Lee data/pensum.csv y data/historial.csv y devuelve EXACTAMENTE las estructuras
definidas en CONTRATO_HERRAMIENTAS.md (mismas que herramientas_stub.py).

Reglas del contrato que se cumplen aquí:
- Solo librería estándar.
- Cada función devuelve un dict (nunca str, nunca print).
- Ante un error esperado no se lanza excepción: se devuelve {"error": "..."}.
- El historial es de un solo estudiante.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from pathlib import Path

NOTA_MINIMA_APROBACION = 3.0
NOTA_MAXIMA = 5.0
MAX_CREDITOS_SEMESTRE = 21

DATA_DIR = Path(__file__).parent / "data"

_PERIODO_RE = re.compile(r"^\d{4}-[12]$")


# ════════════════════════════════════════════════════════════
#  CARGA Y VALIDACIÓN DE LOS CSV
# ════════════════════════════════════════════════════════════
# Los archivos se leen en cada llamada (son pequeños) para que un cambio en
# los CSV se refleje sin reiniciar el agente.

def _leer_pensum():
    """Devuelve (pensum, None) o (None, mensaje_de_error)."""
    ruta = DATA_DIR / "pensum.csv"
    if not ruta.exists():
        return None, f"No se encontró el archivo de datos '{ruta.name}' en la carpeta data/."

    pensum = []
    vistos = set()
    try:
        with open(ruta, encoding="utf-8-sig", newline="") as f:
            for n, fila in enumerate(csv.DictReader(f), start=2):
                codigo = (fila.get("codigo") or "").strip().upper()
                if not codigo:
                    return None, f"pensum.csv, línea {n}: falta el código."
                if codigo in vistos:
                    return None, f"pensum.csv, línea {n}: el código '{codigo}' está repetido."
                try:
                    creditos = int(str(fila.get("creditos")).strip())
                    semestre = int(str(fila.get("semestre")).strip())
                except ValueError:
                    return None, (f"pensum.csv, línea {n}: créditos y semestre de "
                                  f"'{codigo}' deben ser números enteros.")
                if creditos <= 0:
                    return None, f"pensum.csv, línea {n}: los créditos de '{codigo}' deben ser mayores que 0."
                prereqs = [p.strip().upper()
                           for p in (fila.get("prerrequisitos") or "").split(";")
                           if p.strip()]
                vistos.add(codigo)
                pensum.append({
                    "codigo": codigo,
                    "nombre": (fila.get("nombre") or "").strip(),
                    "creditos": creditos,
                    "semestre": semestre,
                    "prerrequisitos": prereqs,
                })
    except (OSError, UnicodeDecodeError, csv.Error) as e:
        return None, f"No se pudo leer pensum.csv: {e}"

    for m in pensum:
        for p in m["prerrequisitos"]:
            if p not in vistos:
                return None, (f"pensum.csv: '{m['codigo']}' tiene como prerrequisito "
                              f"a '{p}', que no existe en el pensum.")
    return pensum, None


def _leer_historial(codigos_pensum: set):
    """Devuelve (historial, None) o (None, mensaje_de_error)."""
    ruta = DATA_DIR / "historial.csv"
    if not ruta.exists():
        return None, f"No se encontró el archivo de datos '{ruta.name}' en la carpeta data/."

    historial = []
    try:
        with open(ruta, encoding="utf-8-sig", newline="") as f:
            for n, fila in enumerate(csv.DictReader(f), start=2):
                codigo = (fila.get("codigo") or "").strip().upper()
                periodo = (fila.get("periodo") or "").strip()
                try:
                    nota = float(str(fila.get("nota")).strip().replace(",", "."))
                except ValueError:
                    return None, f"historial.csv, línea {n}: la nota de '{codigo}' no es un número."
                if codigo not in codigos_pensum:
                    return None, f"historial.csv, línea {n}: la materia '{codigo}' no existe en el pensum."
                if not 0.0 <= nota <= NOTA_MAXIMA:
                    return None, f"historial.csv, línea {n}: la nota {nota} está fuera del rango 0.0 a {NOTA_MAXIMA}."
                if not _PERIODO_RE.match(periodo):
                    return None, f"historial.csv, línea {n}: el periodo '{periodo}' no tiene el formato AAAA-1 o AAAA-2."
                historial.append({"codigo": codigo, "nota": nota, "periodo": periodo})
    except (OSError, UnicodeDecodeError, csv.Error) as e:
        return None, f"No se pudo leer historial.csv: {e}"
    return historial, None


def _cargar():
    """Devuelve (pensum, historial, None) o (None, None, mensaje_de_error)."""
    pensum, error = _leer_pensum()
    if error:
        return None, None, error
    historial, error = _leer_historial({m["codigo"] for m in pensum})
    if error:
        return None, None, error
    return pensum, historial, None


# ════════════════════════════════════════════════════════════
#  FUNCIONES AUXILIARES
# ════════════════════════════════════════════════════════════

def _normalizar(texto) -> str:
    """Quita tildes y pasa a minúsculas: 'Cálculo' -> 'calculo'."""
    sin_tildes = unicodedata.normalize("NFD", str(texto))
    sin_tildes = "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn")
    return sin_tildes.lower().strip()


def _codigo(texto) -> str:
    return str(texto).upper().strip()


def _materia_por_codigo(pensum, codigo):
    codigo = _codigo(codigo)
    for materia in pensum:
        if materia["codigo"] == codigo:
            return materia
    return None


def _codigos_aprobados(historial) -> set:
    """Una materia está aprobada si ALGUNA de sus notas es >= 3.0."""
    return {f["codigo"] for f in historial if f["nota"] >= NOTA_MINIMA_APROBACION}


def _copia(materia: dict) -> dict:
    """Copia para no exponer (ni dejar modificar) las listas internas."""
    return {**materia, "prerrequisitos": list(materia["prerrequisitos"])}


# ════════════════════════════════════════════════════════════
#  HERRAMIENTAS (las 5 del contrato)
# ════════════════════════════════════════════════════════════

def buscar_materia(nombre_o_codigo: str) -> dict:
    """Busca por código exacto o por parte del nombre (sin tildes ni mayúsculas)."""
    pensum, _, error = _cargar()
    if error:
        return {"error": error}

    consulta = _normalizar(nombre_o_codigo)
    if not consulta:
        return {"encontrada": False, "mensaje": "La búsqueda está vacía."}

    # 1. Código exacto
    materia = _materia_por_codigo(pensum, consulta)
    if materia:
        return {"encontrada": True, "materias": [_copia(materia)]}

    # 2. Parte del nombre (puede devolver varias → el agente pide aclarar)
    coincidencias = [_copia(m) for m in pensum if consulta in _normalizar(m["nombre"])]
    if coincidencias:
        return {"encontrada": True, "materias": coincidencias}

    return {"encontrada": False,
            "mensaje": f"No hay materias que coincidan con '{nombre_o_codigo}'."}


def verificar_prerrequisitos(codigo: str) -> dict:
    """Indica si el estudiante cumple los prerrequisitos de una materia."""
    pensum, historial, error = _cargar()
    if error:
        return {"error": error}

    materia = _materia_por_codigo(pensum, codigo)
    if materia is None:
        return {"error": f"La materia '{codigo}' no existe en el pensum."}

    aprobadas = _codigos_aprobados(historial)
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

    pensum, historial, error = _cargar()
    if error:
        return {"error": error}

    aprobadas = _codigos_aprobados(historial)
    disponibles = []
    for m in pensum:
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
    pensum, historial, error = _cargar()
    if error:
        return {"error": error}

    aprobadas = _codigos_aprobados(historial)
    creditos_de = {m["codigo"]: m["creditos"] for m in pensum}

    # Promedio ponderado por créditos con TODAS las notas (incluye perdidas)
    suma = sum(f["nota"] * creditos_de[f["codigo"]] for f in historial)
    total_creditos_cursados = sum(creditos_de[f["codigo"]] for f in historial)
    promedio = round(suma / total_creditos_cursados, 2) if total_creditos_cursados else 0.0

    cursadas = {f["codigo"] for f in historial}
    return {
        "materias_aprobadas": len(aprobadas),
        "materias_pendientes": len(pensum) - len(aprobadas),
        "creditos_aprobados": sum(creditos_de[c] for c in aprobadas),
        "creditos_totales_pensum": sum(creditos_de.values()),
        "promedio_ponderado": promedio,
        "materias_reprobadas_sin_aprobar": sorted(cursadas - aprobadas),
    }


def validar_carga(codigos: list[str]) -> dict:
    """Revisa si un conjunto de materias se puede inscribir junto en un semestre."""
    if not isinstance(codigos, list):
        return {"error": "codigos debe ser una lista, ej: ['MAT201', 'FIS201']."}

    pensum, historial, error = _cargar()
    if error:
        return {"error": error}

    aprobadas = _codigos_aprobados(historial)
    problemas = []
    vistos = set()
    creditos_totales = 0

    for codigo in codigos:
        codigo = _codigo(codigo)
        materia = _materia_por_codigo(pensum, codigo)

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
