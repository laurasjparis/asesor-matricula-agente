# Asesor de Matrícula: agente con herramientas

Agente conversacional que ayuda a un estudiante de Ingeniería de Sistemas a decidir qué materias inscribir, consultando el **pensum** y su **historial de notas** mediante herramientas.

## Integrantes

| Persona | Nombre | Responsabilidad |
|---|---|---|
| A | _[nombre]_ | README, casos de prueba, análisis y guion de demo |
| B | _[nombre]_ | Datos (`pensum.csv`, `historial.csv`) y herramientas (`herramientas.py`) |
| C | _[nombre]_ | Agente (`agente.py`), esquemas, prompt, presupuesto y notebook |

## Problema

Matricularse implica cruzar varias fuentes: qué materias existen, cuáles ya aprobó el estudiante (con repitencias), qué prerrequisitos exige cada una y cuántos créditos suma la carga (máximo 21). Hacerlo a mano es lento y propenso a errores: inscribir una materia ya aprobada, olvidar un prerrequisito o pasarse de créditos.

## ¿Por qué un agente y no un script o un chatbot?

- **Un chatbot solo con LLM inventaría** códigos, créditos y prerrequisitos. Aquí cada dato sale de una herramienta que lee los CSV.
- **Un script fijo no entiende lenguaje natural**: el estudiante dice "Física II" o "Cálculo", no un código. El modelo traduce el nombre a un código (`buscar_materia`) y decide qué herramientas encadenar según la pregunta.
- **La secuencia de pasos no es fija**: una pregunta puede requerir 1 herramienta y otra 4. El agente decide en cada paso, dentro de un presupuesto de llamadas.

## Fuera del alcance

- **No matricula**: solo asesora. El agente nunca dice que inscribió algo.
- Historial de **un solo estudiante** (no hay login ni varios usuarios).
- No considera horarios, cupos, correquisitos, ni reglas especiales de la universidad (homologaciones, créditos mínimos, etc.).
- No modifica los CSV.
- Los datos son de ejemplo; no están conectados al sistema académico real.

## Arquitectura

```
Pregunta → agente.py (loop + presupuesto) ⇄ NVIDIA NIM (LLM con tool use)
                         │
                         └→ herramientas.py → data/pensum.csv, data/historial.csv
```

| Herramienta | Qué hace |
|---|---|
| `buscar_materia` | Busca por código o parte del nombre (sin tildes) |
| `verificar_prerrequisitos` | ¿Cumple los prerrequisitos? ¿Ya la aprobó? |
| `materias_disponibles` | Materias no aprobadas con prerrequisitos cumplidos |
| `resumen_academico` | Aprobadas, créditos, promedio ponderado, perdidas |
| `validar_carga` | Valida un conjunto de materias (máx. 21 créditos) |

Regla de aprobación: nota ≥ 3.0 (escala 0.0–5.0). Con repitencia, la materia cuenta como aprobada si **alguna** nota es ≥ 3.0. Contrato completo en `CONTRATO_HERRAMIENTAS.md`.

## Instrucciones

### En Colab
1. Abrir `demo.ipynb`.
2. En el panel 🔑 **Secretos** crear `NVIDIA_API_KEY` (empieza con `nvapi-`) y activar el acceso al notebook.
3. Ejecutar las celdas en orden.

### Local
```bash
git clone https://github.com/laurasjparis/asesor-matricula-agente.git
cd asesor-matricula-agente
pip install -r requirements.txt
echo "NVIDIA_API_KEY=nvapi-..." > .env      # NUNCA subir este archivo
python ejecutar_casos.py                      # corre los 5 casos y guarda resultados_casos.json
```

Los CSV deben estar en la carpeta `data/`. La clave nunca se escribe en el código ni en el repositorio.

## Fuentes

- Pensum y notas: datos de ejemplo elaborados por el equipo _[indicar origen: pensum real adaptado / inventado]_.
- Agentic loop y control de presupuesto: notebooks de clase `part01_from_prompt_to_action` y `part03`.
- Modelo: `nvidia/nemotron-3.5-super-vl-120b-a12b` vía [NVIDIA NIM](https://build.nvidia.com/).

---

## Datos de referencia (calculados a mano desde los CSV)

Estos valores se calcularon **antes** de correr el agente, directamente de `pensum.csv` e `historial.csv`.

| Dato | Valor | Cómo se obtiene |
|---|---|---|
| Materias en el pensum | 45 | Filas de `pensum.csv` |
| Materias aprobadas | 44 | Todas menos `PT0131` |
| Materias pendientes | 1 | `PT0131` (Período de Práctica, 18 créditos) |
| Créditos aprobados | 131 | 149 − 18 |
| Créditos totales del pensum | 149 | Suma de la columna `creditos` |
| Promedio ponderado | **3.83** | 552.0 / 144 créditos cursados = 3.8333 (usa todas las notas, incluidas las perdidas) |
| Perdidas sin aprobar | ninguna | Las 4 repitencias terminan aprobadas |
| Repitencias | `CM0231` (2.7→3.0), `DF0239` (2.3→3.3), `CM0246` (2.9→3.8), `CM0232` (1.2→4.0) | Códigos con más de una fila |
| Disponibles ahora | solo `PT0131` | No aprobada y sin prerrequisitos |

Nota: `CM0231` se aprobó con **3.0 exacto** (caso borde de la regla `nota >= 3.0`).

---

## Los 5 casos de prueba

Cada caso se definió con su resultado esperado **antes** de ejecutar el agente.

### Caso 1: consulta ambigua

- **Pregunta:** "¿Puedo ver Cálculo?"
- **Presupuesto:** 5
- **Qué se prueba:** que el agente no adivine entre varias materias y pida aclarar (regla 5 del prompt).
- **Esperado (a mano):** `buscar_materia("calculo")` devuelve 3 materias: `CM0230` Cálculo I, `CM0231` Cálculo II, `CM0232` Cálculo III.
- **Respuesta esperada:** lista las tres y pregunta cuál. No afirma que "puede" o "no puede" ninguna sin que el estudiante elija.
- **Falla si:** escoge una por su cuenta o inventa una cuarta.

### Caso 2: materia inexistente

- **Pregunta:** "¿Puedo inscribir Termodinámica?"
- **Presupuesto:** 5
- **Qué se prueba:** que no invente una materia (reglas 2 y 4).
- **Esperado:** `buscar_materia("Termodinámica")` → `{"encontrada": false}`.
- **Respuesta esperada:** dice claramente que no existe en el pensum. No inventa código, créditos ni prerrequisitos.
- **Falla si:** responde con datos de una materia de Termodinámica.

### Caso 3: repitencia y caso borde de nota

- **Pregunta:** "Perdí Física II la primera vez, ¿ya la tengo aprobada?"
- **Presupuesto:** 5
- **Qué se prueba:** repitencia (2.3 en 2023-2 → 3.3 en 2024-2).
- **Esperado:** `buscar_materia("Física II")` → `DF0239` (único resultado, 4 créditos). Luego `verificar_prerrequisitos("DF0239")` → `ya_aprobada: true`, `puede_inscribir: false`, prerrequisito `DF0236` cumplido.
- **Respuesta esperada:** sí está aprobada y no hay que inscribirla de nuevo.
- **Falla si:** dice que está perdida, o cita una nota/periodo (ninguna herramienta devuelve notas individuales, sería inventado).

### Caso 4: carga inválida (exceso de créditos + ya aprobadas)

- **Pregunta:** "Quiero inscribir Período de Práctica, Gestión de Proyectos y Sistemas Operativos. ¿Puedo?"
- **Presupuesto:** 5
- **Qué se prueba:** encadenar herramientas (3 búsquedas + validación) y reportar varios problemas.
- **Esperado:** códigos `PT0131` (18 cr), `ST0277` (3 cr), `ST0257` (4 cr). `validar_carga` → `valida: false`, `creditos_totales: 25`, problemas:
  1. `ST0277`: ya está aprobada.
  2. `ST0257`: ya está aprobada.
  3. Excede el máximo de 21 créditos (25).
- **Respuesta esperada:** no puede; menciona las dos ya aprobadas y los 25 créditos. `PT0131` sí es inscribible por sí sola.
- **Falla si:** da otro total de créditos o dice que puede inscribir las tres.
- Mínimo esperado: 4 tool calls (cabe en el presupuesto de 5).

### Caso 5: presupuesto agotado

- **Pregunta:** "Dame mi promedio, cuántos créditos me faltan y si ya aprobé Física II."
- **Presupuesto:** **1** (a propósito insuficiente: la pregunta necesita 3 llamadas)
- **Qué se prueba:** el límite de llamadas y que el agente avise lo que no pudo verificar.
- **Esperado:** solo se ejecuta la primera tool call; las demás reciben `"presupuesto agotado"`. Si la ejecutada es `resumen_academico`: promedio **3.83**, **131 de 149** créditos aprobados (faltan **18**).
- **Respuesta esperada:** da solo lo verificado y dice explícitamente que no pudo comprobar lo de Física II (o lo que haya quedado sin consultar).
- **Falla si:** afirma algo de Física II sin haberlo consultado, o no avisa que quedó incompleto.

---

## Resultados de la ejecución

> ⏳ **Pendiente:** correr `python ejecutar_casos.py` y pegar aquí lo que salga de `resultados_casos.json` (herramienta, argumentos, resultado, respuesta final). Los valores esperados de arriba **no se modifican** después de correr.

| # | Tool calls (obtenidas) | Coincide con lo esperado | Respuesta final correcta | Veredicto |
|---|---|---|---|---|
| 1 | _pendiente_ | _pendiente_ | _pendiente_ | _pendiente_ |
| 2 | _pendiente_ | _pendiente_ | _pendiente_ | _pendiente_ |
| 3 | _pendiente_ | _pendiente_ | _pendiente_ | _pendiente_ |
| 4 | _pendiente_ | _pendiente_ | _pendiente_ | _pendiente_ |
| 5 | _pendiente_ | _pendiente_ | _pendiente_ | _pendiente_ |

### Traza detallada

_Pegar por caso: `[n] herramienta(argumentos) → resultado` y la respuesta final._

---

## Análisis

### Valoración general
_Escribir tras correr: cuántos casos pasaron, dónde el agente se comportó como se esperaba y dónde no._

### Limitación observada
_Elegir una **que realmente se observe** al correr. Candidatas detectadas al revisar el código (confirmar o descartar):_

1. **Búsqueda por subcadena ambigua.** `buscar_materia("Cálculo II")` también devuelve `Cálculo III` (porque "calculo ii" está dentro de "calculo iii"), y `"Ingeniería de Software"` devuelve también `Tópicos Especiales en Ingeniería de Software`. El agente debe desambiguar por su cuenta.
2. **Nombres que no coinciden literalmente.** `buscar_materia("Introducción a la IA")` devuelve 0 resultados porque el pensum dice "Introducción a Inteligencia Artificial". No hay búsqueda aproximada ni sinónimos.
3. **Las herramientas no devuelven notas ni periodos.** El agente no puede responder "¿con qué nota aprobé X?". Debería decir que no puede verificarlo en vez de inventarlo.
4. **Presupuesto fijo.** Preguntas con varias materias por nombre gastan una llamada por materia solo en buscar códigos.

### Mejora posible
_Ligada a la limitación elegida. Ejemplos:_
- `buscar_materia`: dar prioridad a la coincidencia exacta de nombre sobre la parcial, o aceptar una lista de nombres en una sola llamada para ahorrar presupuesto.
- Agregar búsqueda aproximada (por palabras clave, no por subcadena completa).
- Agregar una herramienta `historial_de_materia(codigo)` que devuelva notas y periodos.

## Estructura del repositorio

```
agente.py                 # loop del agente + esquemas + prompt
herramientas.py           # las 5 herramientas (leen data/*.csv)
herramientas_stub.py      # versión falsa, solo para pruebas
data/pensum.csv
data/historial.csv
CONTRATO_HERRAMIENTAS.md
ejecutar_casos.py         # corre los 5 casos y guarda la traza
demo.ipynb
requirements.txt
```
