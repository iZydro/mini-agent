import os
import json
import importlib.util
import time
import config
from debug import DebugLogger
from transcript import Transcript
from core.tool_result import ToolResult
import inspect
from core.tool_context import ToolContext
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
                "Puedes usar web_search para información reciente o que pueda haber cambiado. "
                "No inventes datos actuales: si hace falta actualidad, busca en Internet. "
            )
        }
    ]


def run_agent(messages, user_input, events, session_id):
    messages.append({
        "role": "user",
        "content": user_input
    })

    events.emit(session_id, "user_message", content=user_input)

    max_steps = 5
    # model = "gpt-4.1-mini"
    model = "gpt-4.1"

    for step in range(1, max_steps + 1):
        events.emit(session_id, "agent_step", step=step)

        events.emit(
            session_id,
            "llm_request",
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
        messages.append(assistant_message)

        tool_calls = assistant_message.tool_calls or []

        if not tool_calls:
            content = assistant_message.content or ""

            events.emit(
                session_id, 
                "llm_final_answer",
                content=content,
                chars=len(content)
            )

            events.emit(
                session_id, 
                "assistant_message",
                content=content
            )

            return content

        events.emit(
            session_id, 
            "llm_tool_calls",
            count=len(tool_calls)
        )

        events.emit(
            session_id, 
            "assistant_message",
            content=assistant_message.content,
            tool_calls=[
                {
                    "id": tool_call.id,
                    "name": tool_call.function.name,
                    "arguments": tool_call.function.arguments
                }
                for tool_call in tool_calls
            ]
        )

        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments or "{}")

            events.emit(
                session_id,
                "tool_start",
                tool=tool_name,
                arguments=arguments
            )

            start = time.time()

            try:
                tool_fn = available_tools[tool_name]

                # tool_result = tool_fn(**arguments)
                context = ToolContext(
                    events=events,
                    session_id=session_id,
                    tool_name=tool_name
                )

                signature = inspect.signature(tool_fn)

                if "context" in signature.parameters:
                    tool_result = tool_fn(context=context, **arguments)
                else:
                    tool_result = tool_fn(**arguments)

                if not isinstance(tool_result, ToolResult):
                    print(f"[legacy tool] {tool_name}")
                    tool_result = ToolResult(
                        content=json.dumps(tool_result, ensure_ascii=False),
                        ui={"legacy_result": tool_result}
                    )

                elapsed_ms = (time.time() - start) * 1000

                events.emit(
                    session_id,
                    "tool_end",
                    tool=tool_name,
                    elapsed_ms=elapsed_ms,
                    ui=tool_result.ui,
                    metrics=tool_result.metrics
                )

            except Exception as e:
                elapsed_ms = (time.time() - start) * 1000

                tool_result = ToolResult(
                    content=json.dumps({"error": str(e)}, ensure_ascii=False),
                    ui={"error": str(e)}
                )

                events.emit(
                    session_id,
                    "tool_error",
                    tool=tool_name,
                    elapsed_ms=elapsed_ms,
                    error=str(e),
                    ui=tool_result.ui
                )

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": tool_result.content
            })

    return "He alcanzado el límite de pasos ejecutando tools."


if __name__ == "__main__":
    from core.event_bus import EventBus
    from listeners.console import ConsoleListener
    from listeners.transcript import TranscriptListener
    from transcript import Transcript

    events = EventBus()
    events.register(ConsoleListener(enabled=True, show_results=False))
    events.register(TranscriptListener(Transcript()))

    session_id = "cli"
    
    messages = create_initial_messages()

    while True:
        user_input = input("\nTú > ")

        if user_input.lower() in ["exit", "quit", "salir"]:
            break

        answer = run_agent(messages, user_input, events, session_id)
        print(f"\nAgente > {answer}")
