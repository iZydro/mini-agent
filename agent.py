import os
import json
import importlib.util
from openai import OpenAI

import config

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

    max_steps = 5

    for step in range(max_steps):
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
            tools=tool_definitions,
            tool_choice="auto",
        )

        assistant_message = response.choices[0].message
        messages.append(assistant_message)

        if not assistant_message.tool_calls:
            return assistant_message.content

        for tool_call in assistant_message.tool_calls:
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments or "{}")

            print(f"\n[tool call] {tool_name}({arguments})")

            tool_fn = available_tools[tool_name]

            try:
                result = tool_fn(**arguments)
            except Exception as e:
                result = {
                    "error": str(e)
                }

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