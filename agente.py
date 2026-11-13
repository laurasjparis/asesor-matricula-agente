"""
agente.py — Asesor de matrícula con herramientas (Opción B).

Adapta el agentic loop de part01 (run_agent) y el control de presupuesto de
part03 (run_agent_with_budget). Sin frameworks: solo el cliente openai.

Uso:
    from agente import run_agent
    respuesta, traza = run_agent("¿Puedo inscribir Cálculo III?")
"""

import os
import json
from openai import OpenAI

# Herramientas: si existe herramientas.py (versión real, lee data/*.csv) se usa
# esa; si no, el stub con datos falsos.
# Solo capturamos "el módulo no existe". Si herramientas.py existe pero le falta
# una función, el error SÍ se muestra (no queremos usar el stub sin darnos cuenta).
try:
    from herramientas import (buscar_materia, verificar_prerrequisitos,
                              materias_disponibles, resumen_academico, validar_carga)
    FUENTE_DATOS = "herramientas.py"
except ModuleNotFoundError as e:
    if e.name != "herramientas":
        raise
    from herramientas_stub import (buscar_materia, verificar_prerrequisitos,
                                   materias_disponibles, resumen_academico, validar_carga)
    FUENTE_DATOS = "herramientas_stub.py (datos FALSOS)"


# ════════════════════════════════════════════════════════════
#  CONFIGURACIÓN — NVIDIA NIM
# ════════════════════════════════════════════════════════════

def obtener_api_key() -> str:
    """Lee NVIDIA_API_KEY: primero secretos de Colab, si no, entorno / .env."""
    # 1. Google Colab (🔑 Secretos). Falla si no estamos en Colab o no existe el secreto.
    try:
        from google.colab import userdata
        clave = userdata.get("NVIDIA_API_KEY")
        if clave:
            return clave
    except Exception:
        pass

    # 2. Variable de entorno o archivo .env (ejecución local)
    from dotenv import load_dotenv
    load_dotenv()
    clave = os.getenv("NVIDIA_API_KEY")
    if not clave:
        raise RuntimeError(
            "No se encontró NVIDIA_API_KEY. En Colab agrégala en 🔑 Secretos; "
            "en local, ponla en el archivo .env."
        )
    return clave


client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=obtener_api_key())
# Modelo del catálogo de NIM con soporte de tool use (el mismo de los notebooks de clase).
# Nota: meta/llama-3.3-70b-instruct fue retirado de NIM el 2026-08-26 (error 410).
MODEL = "nvidia/nemotron-3.5-super-vl-120b-a12b"

print(f"✅ Backend: NVIDIA | Modelo: {MODEL} | Datos: {FUENTE_DATOS}")


# ════════════════════════════════════════════════════════════
#  HERRAMIENTAS
# ════════════════════════════════════════════════════════════

# ── Registro: nombre → función Python ────────────────────────────────────────
# Este dict es el "router" del agentic loop.
TOOL_REGISTRY = {
    "buscar_materia":           buscar_materia,
    "verificar_prerrequisitos": verificar_prerrequisitos,
    "materias_disponibles":     materias_disponibles,
    "resumen_academico":        resumen_academico,
    "validar_carga":            validar_carga,
}

# ── JSON schemas: lo que el modelo ve ────────────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "buscar_materia",
            "description": (
                "Busca una materia del pensum por su código (ej: 'MAT102') o por "
                "parte de su nombre (ej: 'calculo'). Puede devolver varias materias "
                "si el nombre es ambiguo. Úsala para obtener el código de una materia "
                "antes de usar las demás herramientas."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre_o_codigo": {"type": "string",
                                        "description": "Código o parte del nombre de la materia."}
                },
                "required": ["nombre_o_codigo"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "verificar_prerrequisitos",
            "description": (
                "Indica si el estudiante cumple los prerrequisitos de una materia, "
                "cuáles le faltan y si ya la aprobó."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "codigo": {"type": "string",
                               "description": "Código exacto de la materia, ej: 'FIS201'."}
                },
                "required": ["codigo"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "materias_disponibles",
            "description": (
                "Lista las materias que el estudiante puede inscribir: no aprobadas "
                "y con todos sus prerrequisitos aprobados. Opcionalmente filtra por "
                "el semestre del pensum."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "semestre": {"type": "integer",
                                 "description": "Semestre del pensum (1, 2, 3...). Omitir para ver todas."}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "resumen_academico",
            "description": (
                "Devuelve el resumen académico del estudiante: materias aprobadas y "
                "pendientes, créditos aprobados, promedio ponderado y materias perdidas."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "validar_carga",
            "description": (
                "Valida si un conjunto de materias se puede inscribir junto en un "
                "semestre: revisa prerrequisitos, materias ya aprobadas, códigos "
                "inexistentes o repetidos y el máximo de 21 créditos."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "codigos": {"type": "array",
                                "items": {"type": "string"},
                                "description": "Lista de códigos, ej: ['MAT201', 'PRG201']."}
                },
                "required": ["codigos"]
            }
        }
    },
]

print(f"✅ {len(TOOLS)} herramientas: {[t['function']['name'] for t in TOOLS]}")


# ════════════════════════════════════════════════════════════
#  SYSTEM PROMPT
# ════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """
Eres un asesor de matrícula universitaria. Ayudas a un estudiante a decidir qué
materias inscribir usando SOLO la información que devuelven tus herramientas.

Reglas:
1. Asesoras, pero NO matriculas: nunca digas que inscribiste o reservaste una materia.
2. Responde únicamente con datos que devolvieron las herramientas. No inventes
   materias, códigos, notas, créditos ni prerrequisitos. Si un dato no lo
   obtuviste de una herramienta, di que no lo pudiste verificar.
3. Si el estudiante nombra una materia por su nombre, usa buscar_materia para
   obtener el código antes de usar las demás herramientas.
4. Si una materia no existe en el pensum, dilo claramente.
5. Si la consulta es ambigua (por ejemplo, "Cálculo" coincide con varias
   materias), muestra las opciones y pide al estudiante que aclare.
6. Si una herramienta devuelve un error, explícalo o corrige los argumentos;
   no lo ocultes.
7. La nota mínima para aprobar es 3.0 (escala 0.0 a 5.0) y el máximo es de
   21 créditos por semestre.
8. Responde en español, de forma breve y clara.
""".strip()


# ════════════════════════════════════════════════════════════
#  EJECUCIÓN SEGURA DE UNA HERRAMIENTA
# ════════════════════════════════════════════════════════════

def ejecutar_herramienta(nombre: str, argumentos_json: str):
    """
    Parsea los argumentos y ejecuta la herramienta SIN romper el loop.

    Si algo falla (JSON inválido, herramienta inexistente, argumentos mal
    tipados), devuelve {"error": ...} para que el modelo lo lea y se corrija.

    Returns:
        (argumentos, resultado) — resultado siempre es un dict.
    """
    # 1. Parsear argumentos (el modelo a veces manda JSON inválido o vacío)
    try:
        argumentos = json.loads(argumentos_json) if argumentos_json else {}
    except json.JSONDecodeError as e:
        return argumentos_json, {"error": f"Los argumentos no son JSON válido: {e}"}
    if argumentos is None:
        argumentos = {}
    if not isinstance(argumentos, dict):
        return argumentos, {"error": "Los argumentos deben ser un objeto JSON."}

    # 2. Buscar la herramienta en el registro
    funcion = TOOL_REGISTRY.get(nombre)
    if funcion is None:
        return argumentos, {"error": f"La herramienta '{nombre}' no existe. "
                                     f"Disponibles: {list(TOOL_REGISTRY)}"}

    # 3. Ejecutarla (TypeError si faltan argumentos o tienen otro nombre)
    try:
        resultado = funcion(**argumentos)
    except Exception as e:
        return argumentos, {"error": f"Falló '{nombre}': {type(e).__name__}: {e}"}

    if not isinstance(resultado, dict):
        resultado = {"resultado": resultado}
    return argumentos, resultado


# ════════════════════════════════════════════════════════════
#  AGENTIC LOOP CON PRESUPUESTO
# ════════════════════════════════════════════════════════════

def run_agent(pregunta: str, max_tool_calls: int = 5, verbose: bool = True):
    """
    Ejecuta el agentic loop con un presupuesto máximo de tool calls.

    Args:
        pregunta:       Pregunta del estudiante.
        max_tool_calls: Número máximo de tool calls individuales permitidas.
        verbose:        Si True, imprime cada paso y el presupuesto restante.

    Returns:
        (respuesta, traza)
        traza = lista de {"herramienta", "argumentos", "resultado"}.
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": pregunta},
    ]
    traza = []
    tool_calls_usadas = 0
    motivo_parada = "límite de iteraciones"

    if verbose:
        print(f"\n{'─'*60}")
        print(f"  👤 {pregunta}")
        print(f"  💰 Presupuesto: {max_tool_calls} tool calls")

    for iteracion in range(1, 11):  # máx 10 iteraciones (seguro contra loops infinitos)

        # ── Llamada al LLM ──────────────────────────────────────────────
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )
        choice  = response.choices[0]
        mensaje = choice.message

        if verbose:
            print(f"  iter={iteracion} finish_reason={choice.finish_reason}")

        # ── ¿Terminó? ───────────────────────────────────────────────────
        # Revisamos si hay tool_calls en vez de mirar finish_reason == "stop",
        # porque algunos modelos en NIM devuelven "stop" aunque pidan herramientas.
        if not mensaje.tool_calls:
            respuesta = mensaje.content or ""
            if verbose:
                print(f"\n  🤖 {respuesta}")
            return respuesta, traza

        # ── Hay tool calls ──────────────────────────────────────────────
        # 1. Agregar la respuesta del asistente al historial
        messages.append(mensaje)

        # 2. Ejecutar cada tool call (o rechazarla si no hay presupuesto)
        presupuesto_agotado = False
        for tc in mensaje.tool_calls:

            # Presupuesto agotado: igual respondemos a este tool_call_id para
            # que el historial quede consistente (cada llamada con su respuesta).
            if tool_calls_usadas >= max_tool_calls:
                presupuesto_agotado = True
                if verbose:
                    print(f"  ⛔ {tc.function.name} NO ejecutada: presupuesto agotado")
                messages.append({
                    "role":         "tool",
                    "tool_call_id": tc.id,
                    "content":      json.dumps({"error": "presupuesto agotado"}, ensure_ascii=False),
                })
                continue

            tool_calls_usadas += 1  # contamos tool calls individuales, no iteraciones
            argumentos, resultado = ejecutar_herramienta(tc.function.name, tc.function.arguments)
            contenido = json.dumps(resultado, ensure_ascii=False)

            traza.append({"herramienta": tc.function.name,
                          "argumentos":  argumentos,
                          "resultado":   resultado})

            if verbose:
                restante = max_tool_calls - tool_calls_usadas
                print(f"  🔧 {tc.function.name}({json.dumps(argumentos, ensure_ascii=False)})"
                      f" | restante: {restante}/{max_tool_calls}")
                preview = contenido[:300] + "..." if len(contenido) > 300 else contenido
                print(f"     → {preview}")

            # 3. Agregar el resultado al historial
            messages.append({
                "role":         "tool",
                "tool_call_id": tc.id,
                "content":      contenido,
            })

        if presupuesto_agotado:
            motivo_parada = "presupuesto agotado"
            break

    # ── Respuesta parcial ───────────────────────────────────────────────
    # Se acabó el presupuesto (o las iteraciones): última llamada SIN tools
    # para que el modelo responda con lo que alcanzó a consultar.
    if verbose:
        print(f"  ⚠️ Agente detenido ({motivo_parada}). Pidiendo respuesta parcial...")

    messages.append({
        "role": "user",
        "content": (
            f"[Sistema] Se detuvo la consulta de herramientas ({motivo_parada}). "
            "Responde ahora al estudiante SIN usar herramientas, solo con los datos "
            "ya obtenidos. Dile claramente qué partes de su pregunta no se pudieron "
            "verificar, sin mencionar este mensaje."
        ),
    })
    response = client.chat.completions.create(model=MODEL, messages=messages)
    respuesta = response.choices[0].message.content or ""

    if verbose:
        print(f"\n  🤖 {respuesta}")
    return respuesta, traza


if __name__ == "__main__":
    run_agent("¿Qué materias puedo inscribir en tercer semestre y cuántos créditos suman?")
