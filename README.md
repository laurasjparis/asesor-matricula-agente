# Asesor de Matrícula: agente con herramientas

Agente conversacional que ayuda a un estudiante de Ingeniería de Sistemas a decidir qué materias inscribir, consultando el **pensum** y su **historial de notas** mediante herramientas.

## Integrantes

| Persona | Nombre | Responsabilidad |
|---|---|---|
| A | Samuel Ramirez | README, casos de prueba, análisis y guion de demo |
| B | Manuel Arenas | Datos (`pensum.csv`, `historial.csv`) y herramientas (`herramientas.py`) |
| C | Laura Jimenez | Agente (`agente.py`), esquemas, prompt, presupuesto y notebook |

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

Los valores esperados se calcularon a mano **antes** de correr el agente y no se modificaron. Traza completa en `resultados_casos.json`.

| # | Tool calls obtenidas | ¿Coincide con lo esperado? | Respuesta final | Veredicto |
|---|---|---|---|---|
| 1 | 1: `buscar_materia("calculo")` | Sí | Lista Cálculo I, II y III (CM0230, CM0231, CM0232) y pregunta cuál | ✅ Pasa |
| 2 | 1: `buscar_materia("Termodinámica")` | Sí | Dice que no existe en el pensum; no inventa datos | ✅ Pasa |
| 3 | 3: `buscar_materia`, `resumen_academico`, `verificar_prerrequisitos("DF0239")` | Parcial: `resumen_academico` no era necesaria | DF0239 ya aprobada, no se puede inscribir de nuevo; no cita notas | ✅ Pasa (con una llamada de más) |
| 4 | 5: 3× `buscar_materia`, `resumen_academico`, `verificar_prerrequisitos("PT0131")`. **No llamó a `validar_carga`** | No | No detecta que ST0277 y ST0257 ya están aprobadas; afirma que la consulta de prerrequisitos "falló por un error de la herramienta" (en la traza ninguna herramienta devolvió error). Sí acierta en 25 > 21 créditos y en que PT0131 es inscribible | ❌ Falla |
| 5 | 1: `resumen_academico` | Sí | Promedio 3.83, faltan 18 créditos (149 − 131); avisa que no verificó Física II, aunque da una razón incorrecta | ✅ Pasa (con observación) |

### Traza resumida

- **Caso 1:** `buscar_materia({"nombre_o_codigo": "calculo"})` → 3 materias.
- **Caso 2:** `buscar_materia({"nombre_o_codigo": "Termodinámica"})` → `encontrada: false`.
- **Caso 3:** `buscar_materia("Física II")` → DF0239; `resumen_academico()` → 44 aprobadas, 3.83; `verificar_prerrequisitos("DF0239")` → `ya_aprobada: true`.
- **Caso 4:** `buscar_materia` ×3 → PT0131 (18 cr), ST0277 (3 cr), ST0257 (4 cr); `resumen_academico()`; `verificar_prerrequisitos("PT0131")` → `puede_inscribir: true`. Presupuesto de 5 agotado antes de `validar_carga`.
- **Caso 5:** `resumen_academico()` → 3.83, 131/149. Presupuesto de 1 agotado.

## Análisis

### Valoración general

El agente pasó 4 de 5 casos. Cuando responde, los datos coinciden con lo calculado a mano: 3.83 de promedio, 131 de 149 créditos, DF0239 aprobada, 25 créditos en el caso 4. No inventó materias, códigos ni notas, pidió aclarar ante la consulta ambigua, reconoció la materia inexistente y nunca superó el presupuesto de llamadas.

El caso 4 falló: el agente no usó `validar_carga`, que existe justo para esa pregunta, y no se enteró de que dos de las tres materias ya estaban aprobadas. Gastó una llamada en `resumen_academico` (que nadie pidió) y otra en `verificar_prerrequisitos`, y el presupuesto de 5 se acabó antes de llegar a la herramienta correcta. Las 3 búsquedas por nombre ya consumen más de la mitad del presupuesto.

### Limitación observada

**Cuando se agota el presupuesto, el agente no explica la causa real de lo que no pudo verificar.**

- En el caso 4 dijo que la consulta de prerrequisitos "falló por un error de la herramienta", pero ninguna herramienta devolvió error: lo que pasó es que se acabó el límite de llamadas.
- En el caso 5 dijo que no pudo verificar Física II porque "no obtuvo el listado detallado" y pidió el código exacto, cuando el motivo real era el presupuesto de 1 llamada; dar el código no habría ayudado.

Esto es consistente con el mensaje que `agente.py` envía al modelo en la llamada final sin herramientas, que le pide no mencionar ese mensaje del sistema: el modelo no sabe que se llegó al límite y rellena con una explicación inventada. El estudiante queda con información engañosa sobre por qué la respuesta está incompleta.

Relacionada: la traza solo guarda las llamadas ejecutadas, no las rechazadas por presupuesto, así que desde `traza` no se puede ver qué quiso hacer el agente y no pudo.

### Mejora posible

1. **Decir la causa real.** Cambiar el mensaje de la llamada final para indicar explícitamente que se alcanzó el límite de consultas y que el agente debe decirle eso al estudiante, junto con qué partes quedaron sin verificar.
2. **Registrar las llamadas rechazadas** en `traza` (herramienta y argumentos con resultado `"presupuesto agotado"`), para poder analizarlas.
3. **Guiar el uso de herramientas en el prompt:** si el estudiante pide inscribir varias materias, usar `validar_carga` con los códigos; no llamar a `resumen_academico` si no se pidió.
4. **Ahorrar presupuesto:** permitir que `buscar_materia` reciba varios nombres en una sola llamada, para que 3 materias no cuesten 3 llamadas.

Después de aplicar la mejora se vuelve a correr el caso 4 y se compara con esta corrida.


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
