import os
import json
import importlib.util
import time
import config
from debug import DebugLogger
from transcript import Transcript
from openai import OpenAI

client = OpenAI()


def load_tools(base_dir="tools"):
    definitions = []
    executors = {}

    for root, dirs, files in os.walk(base_dir):
        if "tool.py" not in files:
            continue

        tool_path = os.path.join(root, "tool.py")
        module_name = tool_path.replace("/", ".").replace("\\", ".")[:-3]

        spec = importlib.util.spec_from_file_location(module_name, tool_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        tool = module.Tool()

        definitions.append(tool.definition)
        executors[tool.name] = tool.execute

        print(f"[tool loaded] {tool.name} from {tool_path}")

    return definitions, executors

tool_definitions, available_tools = load_tools()

debug = DebugLogger(
    enabled=True,
    show_results=False,
    max_result_chars=3000
)

transcript = Transcript()


def create_initial_messages():
    return [
        {
            "role": "system",
            "content": (
                "Eres un agente local sencillo. "
                "Puedes usar tools locales cuando necesites información real. "
                "Recuerda la información obtenida durante la conversación. "
                "Nunca digas que vas a hacer algo más tarde o que el usuario espere. "
                "Si necesitas otra tool para completar la tarea, llámala directamente. "
                "Cuando tengas información suficiente, responde al usuario."
            )
        }
    ]


def run_agent(messages, user_input):
    messages.append({
        "role": "user",
        "content": user_input
    })

    transcript.write("user_message", {
        "content": user_input
    })

    max_steps = 5
    # model = "gpt-4.1-mini"
    model = "gpt-4.1"

    for step in range(1, max_steps + 1):
        debug.step(step)
        debug.model_request(
            model=model,
            messages_count=len(messages),
            tools_count=len(tool_definitions)
        )

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tool_definitions,
            tool_choice="auto",
        )

        assistant_message = response.choices[0].message

        transcript.write("assistant_message", {
            "content": assistant_message.content,
            "tool_calls": [
                {
                    "id": tool_call.id,
                    "name": tool_call.function.name,
                    "arguments": tool_call.function.arguments
                }
                for tool_call in (assistant_message.tool_calls or [])
            ]
        })

        messages.append(assistant_message)

        debug.model_response(assistant_message)

        if not assistant_message.tool_calls:
            return assistant_message.content

        for tool_call in assistant_message.tool_calls:
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments or "{}")

            transcript.write("tool_start", {
                "name": tool_name,
                "arguments": arguments
            })

            debug.tool_start(tool_name, arguments)
            start = time.time()

            try:
                tool_fn = available_tools[tool_name]
                result = tool_fn(**arguments)
                elapsed_ms = (time.time() - start) * 1000
                debug.tool_end(tool_name, result, elapsed_ms)

            except Exception as e:
                elapsed_ms = (time.time() - start) * 1000
                result = {
                    "error": str(e)
                }
                debug.tool_error(tool_name, e, elapsed_ms)

            transcript.write("tool_result", {
                "name": tool_name,
                "elapsed_ms": elapsed_ms,
                "result": result
            })

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result, ensure_ascii=False)
            })

    return "He alcanzado el límite de pasos ejecutando tools."


if __name__ == "__main__":
    messages = create_initial_messages()

    while True:
        user_input = input("\nTú > ")

        if user_input.lower() in ["exit", "quit", "salir"]:
            break

        answer = run_agent(messages, user_input)
        print(f"\nAgente > {answer}")