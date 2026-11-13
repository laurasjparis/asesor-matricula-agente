# Contrato: herramientas.py ↔ agente.py

Este documento fija lo que `herramientas.py` debe cumplir para que el agente
lo use sin cambios. **Si algo de aquí necesita cambiar, avisar antes**: el
agente tiene escrito a mano el JSON schema de cada función.

## 1. Reglas generales

- Archivo: `herramientas.py` en la raíz del repo.
- Solo librería estándar (`csv`, `pathlib`). Si se necesita `pandas`, agregarlo
  a `requirements.txt` y avisar.
- Leer los CSV con ruta relativa al archivo, para que funcione en Colab y local:
  ```python
  from pathlib import Path
  DATA_DIR = Path(__file__).parent / "data"
  ```
- Cada función **devuelve un `dict`** (nunca `str`, nunca `print`).
- Ante un error esperado (materia inexistente, dato inválido) **no lanzar
  excepción**: devolver `{"error": "mensaje claro en español"}`.
- Constantes al inicio del archivo:
  ```python
  NOTA_MINIMA_APROBACION = 3.0
  NOTA_MAXIMA = 5.0
  MAX_CREDITOS_SEMESTRE = 21
  ```
- El historial es de **un solo estudiante**.

## 2. Datos

### `data/pensum.csv`

UTF-8, separado por comas, con encabezado:

```csv
codigo,nombre,creditos,semestre,prerrequisitos
MAT101,Cálculo I,4,1,
MAT102,Cálculo II,4,2,MAT101
FIS201,Física Mecánica,4,3,MAT101;MAT102
```

| Columna | Tipo | Notas |
|---|---|---|
| `codigo` | texto | Único. Mayúsculas, sin espacios. |
| `nombre` | texto | Con tildes normales. |
| `creditos` | entero | Mayor que 0. |
| `semestre` | entero | Semestre sugerido en el pensum (1, 2, 3…). |
| `prerrequisitos` | texto | Códigos separados por `;`. Vacío si no tiene. |

### `data/historial.csv`

```csv
codigo,nota,periodo
MAT101,3.8,2025-1
MAT102,2.5,2025-2
MAT102,3.4,2026-1
```

| Columna | Tipo | Notas |
|---|---|---|
| `codigo` | texto | Debe existir en `pensum.csv`. |
| `nota` | decimal | Entre 0.0 y 5.0. Punto decimal (`3.8`, no `3,8`). |
| `periodo` | texto | Formato `AAAA-1` o `AAAA-2`. |

- **No hay columna `estado`**: se calcula. Aprobada si `nota >= 3.0`.
- Una materia puede aparecer varias veces (repitencia). Cuenta como
  **aprobada si alguna de sus notas es ≥ 3.0**.

## 3. Funciones

Los nombres de función y de parámetro deben ser **exactamente** estos.

### `buscar_materia(nombre_o_codigo: str) -> dict`

Busca por código exacto o por parte del nombre, sin importar mayúsculas ni
tildes (`"calculo"` encuentra `"Cálculo I"` y `"Cálculo II"`).

```python
# Encontrada (una o varias; si son varias, el agente pide aclarar)
{"encontrada": True,
 "materias": [{"codigo": "MAT102", "nombre": "Cálculo II", "creditos": 4,
               "semestre": 2, "prerrequisitos": ["MAT101"]}]}

# No encontrada
{"encontrada": False, "mensaje": "No hay materias que coincidan con 'xyz'."}
```

### `verificar_prerrequisitos(codigo: str) -> dict`

```python
{"codigo": "FIS201", "nombre": "Física Mecánica",
 "ya_aprobada": False,
 "prerrequisitos_cumplidos": ["MAT101"],
 "prerrequisitos_faltantes": ["MAT102"],
 "puede_inscribir": False}
```

- `puede_inscribir` es `True` solo si no está aprobada y no le faltan
  prerrequisitos.
- Código inexistente: `{"error": "La materia 'XXX' no existe en el pensum."}`

### `materias_disponibles(semestre: int | None = None) -> dict`

Materias **no aprobadas** cuyos prerrequisitos **están todos aprobados**.
Si se pasa `semestre`, filtra por la columna `semestre` del pensum.

```python
{"semestre": 3,          # None si no se filtró
 "total": 2,
 "materias": [{"codigo": "FIS201", "nombre": "Física Mecánica",
               "creditos": 4, "semestre": 3}]}
```

### `resumen_academico() -> dict`

```python
{"materias_aprobadas": 12,
 "materias_pendientes": 30,        # del pensum, aún no aprobadas
 "creditos_aprobados": 44,
 "creditos_totales_pensum": 160,
 "promedio_ponderado": 3.85,       # por créditos, todas las notas, 2 decimales
 "materias_reprobadas_sin_aprobar": ["QUI101"]}  # perdidas y aún no aprobadas
```

### `validar_carga(codigos: list[str]) -> dict`

Revisa si un conjunto de materias se puede inscribir junto en un semestre.

```python
{"valida": False,
 "creditos_totales": 23,
 "max_creditos": 21,
 "problemas": [
     {"codigo": "FIS201", "motivo": "Faltan prerrequisitos: MAT102"},
     {"codigo": None,     "motivo": "Excede el máximo de 21 créditos (23)."}]}
```

Motivos a revisar: código inexistente, materia ya aprobada, código repetido,
prerrequisitos faltantes y exceso de créditos. `valida` es `True` solo si
`problemas` está vacío. Los códigos inexistentes no suman créditos.

## 4. Prueba rápida antes de subir

```python
from herramientas import *
print(buscar_materia("calculo"))
print(verificar_prerrequisitos("NOEXISTE"))   # debe devolver {"error": ...}
print(materias_disponibles(2))
print(resumen_academico())
print(validar_carga(["MAT101", "MAT101"]))      # repetida → problema
```

Mientras tanto, el agente usa `herramientas_stub.py`, que tiene datos falsos y
devuelve exactamente estas estructuras.
