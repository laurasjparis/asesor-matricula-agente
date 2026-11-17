# Asesor de Matrícula: agente con herramientas

[![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/laurasjparis/asesor-matricula-agente/blob/main/demo.ipynb)

Agente conversacional que ayuda a un estudiante de Ingeniería de Sistemas a decidir qué materias inscribir, consultando el **pensum** y su **historial de notas** mediante herramientas.

**Opción elegida: B, agente con herramientas** (proyecto final de SI3003 Inteligencia Artificial).

## Integrantes

| Persona | Nombre | Responsabilidad |
|---|---|---|
| A | Samuel Ramirez | README, casos de prueba y análisis|
| B | Manuel Arenas | Datos (`pensum.csv`, `historial.csv`) y herramientas (`herramientas.py`) |
| C | Laura Jimenez | Agente (`agente.py`), esquemas, prompt, presupuesto y notebook |

## Problema

Matricularse implica cruzar varias fuentes: qué materias existen, cuáles ya aprobó el estudiante (con repitencias), qué prerrequisitos exige cada una y cuántos créditos suma la carga (máximo 21). Hacerlo a mano es lento y propenso a errores: inscribir una materia ya aprobada, olvidar un prerrequisito o pasarse de créditos.

## Qué tareas atiende

- Buscar una materia por código o nombre (sin importar tildes ni mayúsculas).
- Verificar si el estudiante cumple los prerrequisitos de una materia o si ya la aprobó.
- Listar las materias que puede inscribir (opcionalmente por semestre).
- Resumir su avance: materias y créditos aprobados, promedio ponderado y materias perdidas.
- Validar si un conjunto de materias se puede inscribir junto (prerrequisitos, ya aprobadas, máximo 21 créditos).

## ¿Por qué un agente y no un script o un chatbot?

- **Un chatbot solo con LLM inventaría** códigos, créditos y prerrequisitos. Aquí cada dato sale de una herramienta que lee los CSV.
- **Un script fijo no entiende lenguaje natural**: el estudiante dice "Física II" o "Cálculo", no un código. El modelo traduce el nombre a un código (`buscar_materia`) y decide qué herramientas encadenar según la pregunta.
- **La secuencia de pasos no es fija**: una pregunta puede requerir 1 herramienta y otra 4. El agente decide en cada paso, dentro de un presupuesto de llamadas.

## Fuera del alcance

- **No matricula**: solo asesora. El agente nunca dice que inscribió algo.
- Historial de **un solo estudiante** (no hay login ni varios usuarios).
- No considera horarios, cupos, correquisitos, ni reglas especiales de la universidad (homologaciones, créditos mínimos, etc.).
- No modifica los CSV.
- Los datos son dos archivos CSV estáticos (pensum de Ingeniería de Sistemas de EAFIT e historial de un integrante); no están conectados al sistema académico real.

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

Regla de aprobación: nota ≥ 3.0 (escala 0.0–5.0). Con repitencia, la materia cuenta como aprobada si **alguna** nota es ≥ 3.0.

### Cómo calcula cada herramienta

- **Aprobada:** una materia está aprobada si **alguna** de sus notas es ≥ 3.0 (escala 0.0 a 5.0).
- `buscar_materia`: código exacto o parte del nombre, sin tildes ni mayúsculas (`"calculo"` encuentra Cálculo I, II y III).
- `verificar_prerrequisitos`: faltantes = prerrequisitos aún no aprobados. `puede_inscribir` es verdadero solo si la materia no está aprobada y no le falta ninguno.
- `materias_disponibles`: materias no aprobadas cuyos prerrequisitos están todos aprobados (opcionalmente de un semestre).
- `resumen_academico`: **promedio ponderado = Σ (nota × créditos) / Σ créditos**, contando todos los intentos (incluidas las notas perdidas). También entrega materias y créditos aprobados y las perdidas sin aprobar.
- `validar_carga`: suma los créditos de los códigos válidos y no repetidos, y reporta como problemas: código inexistente, repetido, materia ya aprobada, prerrequisitos faltantes y exceso sobre 21 créditos.

### Límite de llamadas a herramientas

El agente tiene un presupuesto de **5 tool calls por pregunta** (parámetro `max_tool_calls` de `run_agent`; cada llamada individual cuenta). Cuando se alcanza:

1. Las llamadas que el modelo siga pidiendo **no se ejecutan**: cada una recibe como respuesta que el presupuesto se agotó.
2. Se hace una última llamada al modelo **sin herramientas**, para que responda con lo que alcanzó a consultar.
3. Esa respuesta debe indicar qué partes de la pregunta no se pudieron verificar.

Además hay un tope de 10 iteraciones del loop como seguro contra ciclos infinitos.

## Instrucciones

### En Colab
1. Abrir el notebook directamente en Colab: [**demo.ipynb**](https://colab.research.google.com/github/laurasjparis/asesor-matricula-agente/blob/main/demo.ipynb).
2. En el panel 🔑 **Secretos** crear `NVIDIA_API_KEY` con **tu propia clave** de [build.nvidia.com](https://build.nvidia.com/) (empieza con `nvapi-`) y activar el acceso al notebook. La clave no viene incluida en el repositorio.
3. Ejecutar las celdas en orden.

### Local
```bash
git clone https://github.com/laurasjparis/asesor-matricula-agente.git
cd asesor-matricula-agente
pip install -r requirements.txt
echo "NVIDIA_API_KEY=nvapi-..." > .env      # NUNCA subir este archivo
python verificar_esperados.py                 # comprueba los valores calculados a mano contra los CSV
python ejecutar_casos.py                      # corre los 5 casos y guarda resultados_casos.json
```

Los CSV deben estar en la carpeta `data/`. La clave nunca se escribe en el código ni en el repositorio.

## Fuentes

- Pensum y notas: plan de estudios de Ingeniería de Sistemas de la universidad EAFIT e historial de uno de los miembros del grupo, usado con su autorización.
- Agentic loop y control de presupuesto: notebooks de clase `part01_from_prompt_to_action` y `part03`.
- Modelo: `nvidia/nemotron-3.5-super-vl-120b-a12b` vía [NVIDIA NIM](https://build.nvidia.com/).

---

## Datos de referencia (calculados a mano desde los CSV)

Estos valores se calcularon **antes** de correr el agente, directamente de `pensum.csv` e `historial.csv` (23 filas).

| Dato | Valor | Cómo se obtiene |
|---|---|---|
| Materias en el pensum | 45 | Filas de `pensum.csv` |
| Materias aprobadas | 19 | Códigos con alguna nota ≥ 3.0 |
| Materias pendientes | 26 | 45 − 19 |
| Créditos aprobados | 53 | Suma de créditos de las aprobadas |
| Créditos totales del pensum | 149 | Suma de la columna `creditos` |
| Créditos que faltan | 96 | 149 − 53 |
| Promedio ponderado | **3.65** | 241.1 / 66 créditos cursados = 3.653 (usa todas las notas, incluidas las perdidas) |
| Perdidas sin aprobar | `CM0232` (1.2), `CM0246` (2.9), `DF0239` (2.3) | Códigos cuya única o mejor nota es < 3.0 |
| Repitencia aprobada | `CM0231` (2.7 → 3.0) | Código con dos filas y alguna ≥ 3.0 |
| Prerrequisito faltante | `ST0257` necesita `ST0254` (aún no cursada) | Pensum vs. aprobadas |

Nota: `CM0231` se aprobó con **3.0 exacto** (caso borde de la regla `nota >= 3.0`).

> Los esperados se recalcularon cuando el equipo acortó `historial.csv` para tener materias perdidas y prerrequisitos faltantes. Se hizo **antes** de volver a correr el agente con los datos nuevos. La corrida anterior (con el historial completo, 44 de 45 aprobadas) se conserva en `resultados_casos_antes.json`.

---

## Los 5 casos de prueba

Cada caso se definió con su resultado esperado **antes** de ejecutar el agente. Categorías: casos habituales (3, 4, 5), casos que exigen herramientas (todos) y casos límite (1 y 2).

### Caso 1: consulta ambigua _(caso límite)_

- **Pregunta:** "¿Puedo ver Cálculo?"
- **Presupuesto:** 5
- **Qué se prueba:** que el agente no adivine entre varias materias y pida aclarar.
- **Esperado (a mano):** `buscar_materia("calculo")` devuelve 3 materias: `CM0230` Cálculo I, `CM0231` Cálculo II, `CM0232` Cálculo III.
- **Respuesta esperada:** lista las tres y pregunta cuál. No afirma que "puede" o "no puede" sin que el estudiante elija.
- **Falla si:** escoge una por su cuenta o inventa una cuarta.

### Caso 2: materia inexistente _(caso límite)_

- **Pregunta:** "¿Puedo inscribir Termodinámica?"
- **Presupuesto:** 5
- **Qué se prueba:** que no invente una materia.
- **Esperado:** `buscar_materia("Termodinámica")` → `{"encontrada": false}`. El prompt permite reintentar una vez con una palabra más corta, así que **1 o 2 búsquedas** son válidas; en ambas debe terminar diciendo que no existe.
- **Respuesta esperada:** dice claramente que no existe en el pensum. No inventa código, créditos ni prerrequisitos.
- **Falla si:** responde con datos de una materia de Termodinámica.

### Caso 3: materia perdida que sigue sin aprobar _(habitual)_

- **Pregunta:** "Perdí Física II la primera vez, ¿ya la tengo aprobada?"
- **Presupuesto:** 5
- **Qué se prueba:** que no dé por aprobada una materia que el estudiante perdió y no ha vuelto a ver.
- **Esperado:** `buscar_materia("Física II")` → `DF0239` (único resultado, 4 créditos). Luego `verificar_prerrequisitos("DF0239")` → `ya_aprobada: false`, `puede_inscribir: true`, prerrequisito `DF0236` cumplido.
- **Respuesta esperada:** **no** está aprobada; puede inscribirla de nuevo porque cumple el prerrequisito.
- **Falla si:** dice que está aprobada, o cita una nota/periodo (ninguna herramienta devuelve notas individuales; sería inventado).

### Caso 4: carga inválida (prerrequisito faltante + exceso de créditos) _(habitual)_

- **Pregunta:** "Quiero inscribir Período de Práctica, Gestión de Proyectos y Sistemas Operativos. ¿Puedo?"
- **Presupuesto:** 5
- **Qué se prueba:** encadenar herramientas (3 búsquedas + validación) y reportar varios problemas.
- **Esperado:** códigos `PT0131` (18 cr), `ST0277` (3 cr), `ST0257` (4 cr). `validar_carga` → `valida: false`, `creditos_totales: 25`, problemas:
  1. `ST0257`: faltan prerrequisitos: `ST0254`.
  2. Excede el máximo de 21 créditos (25).
- **Respuesta esperada:** no puede inscribir las tres; menciona el prerrequisito faltante de Sistemas Operativos y los 25 créditos. `PT0131` y `ST0277` no tienen problema propio (el problema es la suma).
- **Falla si:** da otro total de créditos, dice que puede inscribir las tres, o no menciona el prerrequisito `ST0254`.
- Mínimo esperado: 4 tool calls (cabe en el presupuesto de 5).

### Caso 5: presupuesto agotado _(habitual, con límite de llamadas)_

- **Pregunta:** "Dame mi promedio, cuántos créditos me faltan y si ya aprobé Física II."
- **Presupuesto:** **1** (a propósito insuficiente: la pregunta necesita 3 llamadas)
- **Qué se prueba:** el límite de llamadas y que el agente avise lo que no pudo verificar.
- **Esperado:** solo se ejecuta la primera tool call; las demás se rechazan por presupuesto. Si la ejecutada es `resumen_academico`: promedio **3.65**, **53 de 149** créditos aprobados (faltan **96**).
- **Respuesta esperada:** da solo lo verificado y dice explícitamente que no pudo comprobar lo de Física II porque se alcanzó el límite de consultas.
- **Falla si:** afirma algo de Física II sin haberlo consultado, o no avisa que quedó incompleto.

---

## Resultados de la ejecución

### Primera corrida (historial anterior: 44 de 45 materias aprobadas)

Con el historial completo, el agente pasó 4 de 5 casos y falló el caso 4: no llamó a `validar_carga` (usó `resumen_academico` y `verificar_prerrequisitos`), agotó las 5 llamadas y dijo que "la consulta de prerrequisitos falló por un error de la herramienta", aunque ninguna herramienta devolvió error. Traza completa en `resultados_casos_antes.json`.

### Segunda corrida (historial actual: 19 de 45 aprobadas)

Los esperados de arriba se calcularon antes de esta corrida y no se modificaron. Traza completa en `resultados_casos.json`.

| # | Tool calls obtenidas | ¿Coincide con lo esperado? | Respuesta final | Veredicto |
|---|---|---|---|---|
| 1 | 1: `buscar_materia("calculo")` | Sí | Lista Cálculo I, II y III (CM0230, CM0231, CM0232) y pregunta cuál | ✅ Pasa |
| 2 | 2: `buscar_materia("Termodinámica")` y `buscar_materia("Termo")` | Sí (el prompt permite un reintento) | Dice que no aparece en el pensum; no inventa datos | ✅ Pasa |
| 3 | 2: `resumen_academico`, `buscar_materia("Física II")` | Parcial: no llamó a `verificar_prerrequisitos` | "No la tienes aprobada": DF0239 está entre las perdidas sin aprobar. No dice que puede inscribirla de nuevo | ⚠️ Pasa con observaciones |
| 4 | 4: 3× `buscar_materia`, `validar_carga(["PT0131","ST0277","ST0257"])` | Sí | No puede: 25 créditos contra un máximo de 21 y `ST0257` requiere `ST0254` | ✅ Pasa |
| 5 | 1: `resumen_academico` (la siguiente, `buscar_materia`, fue rechazada por presupuesto) | Sí | Promedio 3.65 y faltan 96 créditos; avisa que no verificó Física II, pero no dice que el motivo fue el límite de consultas | ⚠️ Pasa con observaciones |

### Traza resumida

- **Caso 1:** `buscar_materia({"nombre_o_codigo": "calculo"})` → 3 materias.
- **Caso 2:** `buscar_materia("Termodinámica")` → `encontrada: false`; `buscar_materia("Termo")` → `encontrada: false`.
- **Caso 3:** `resumen_academico()` → 19 aprobadas, 3.65, perdidas sin aprobar `CM0232`, `CM0246`, `DF0239`; `buscar_materia("Física II")` → `DF0239`.
- **Caso 4:** `buscar_materia` ×3 → `PT0131` (18 cr), `ST0277` (3 cr), `ST0257` (4 cr); `validar_carga` → `valida: false`, 25 créditos, problemas: `ST0257` (falta `ST0254`) y exceso de créditos.
- **Caso 5:** `resumen_academico()` → 53 de 149 créditos, 3.65; segunda llamada (`buscar_materia`) rechazada: presupuesto agotado.

## Análisis

### Valoración general

Ningún caso cumplió una de sus condiciones de falla: tres pasaron sin observaciones y dos con observaciones. Los números coinciden con lo calculado a mano (3.65 de promedio, 96 créditos por completar, 25 créditos en el caso 4). El agente no inventó materias, códigos ni notas, pidió aclarar ante la consulta ambigua, reconoció la materia inexistente y nunca superó el presupuesto de llamadas. Cubre además los tres tipos de decisión que pide el problema: **puede** (caso 3, Física II es inscribible), **no puede** (caso 4) y **no pertenece al programa** (caso 2).

Hay que leer estos resultados con cuidado:

- **Es una sola corrida por caso** y el modelo no es determinista. En la primera corrida el caso 4 falló; en la segunda pasó. Entre ambas cambiaron los datos (historial acortado) y el prompt del agente (se agregó la regla de reintentar la búsqueda), así que no podemos atribuir la mejora a una causa concreta ni afirmar que el caso 4 esté resuelto.
- **Caso 3:** la respuesta es correcta y se apoya en una herramienta (`resumen_academico` lista a `DF0239` como perdida sin aprobar), pero el agente no usó la herramienta pensada para esa pregunta y no dijo que la materia se puede inscribir de nuevo. La verificación automática lo marcó, y no se cambió el criterio después de ver el resultado.
- **Caso 4:** la respuesta incluye una palabra en inglés ("appears") dentro de una frase en español.

### Limitación observada

**Cuando se agota el presupuesto, el agente no explica la causa real de lo que no pudo verificar.**

- En el caso 5 la terminal muestra que se rechazó la llamada `buscar_materia` por presupuesto agotado, pero la respuesta dice que "no obtuvo el detalle de tus materias por código o nombre", como si fuera un problema de datos. El estudiante no se entera de que el agente alcanzó su límite de consultas.
- En la primera corrida, el caso 4 mostró lo mismo de forma más grave: habló de un "error de la herramienta" que no existió.

La causa está en `agente.py`: el mensaje que se envía al modelo para la respuesta final le pide no mencionar ese mensaje del sistema, así que el modelo no sabe que se alcanzó el límite. Relacionado: la `traza` solo guarda las llamadas ejecutadas, no las rechazadas, así que `resultados_casos.json` no muestra lo que el agente quiso hacer y no pudo.

### Mejora posible

1. **Decir la causa real:** cambiar el mensaje final para indicar que se alcanzó el límite de consultas y que debe decírselo al estudiante junto con lo que quedó sin verificar.
2. **Registrar las llamadas rechazadas** en `traza`, marcadas como no ejecutadas, para poder analizarlas.
3. **Guiar el uso de herramientas en el prompt:** `validar_carga` cuando se piden varias materias, `verificar_prerrequisitos` para "¿puedo ver X?", y mencionar si una materia se puede inscribir de nuevo.
4. **Ahorrar presupuesto:** que `buscar_materia` acepte varios nombres en una llamada. Hoy cada materia nombrada cuesta una llamada.

Estas mejoras quedan como propuesta; no se aplicaron en esta versión.

## Estructura del repositorio

```
agente.py                    # loop del agente + esquemas + prompt
herramientas.py              # las 5 herramientas (leen data/*.csv)
data/pensum.csv
data/historial.csv
demo.ipynb                   # demo para Colab
ejecutar_casos.py            # corre los 5 casos y guarda la traza
verificar_esperados.py       # valores esperados calculados a mano
resultados_casos.json        # última corrida
resultados_casos_antes.json  # primera corrida (historial anterior)
prueba.py                    # prueba rápida de conexión con NVIDIA NIM
referencia/                  # notebooks de clase usados como base
requirements.txt
LICENSE
```
