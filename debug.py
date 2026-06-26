import json
import time


class DebugLogger:
    def __init__(self, enabled=True, show_results=True, max_result_chars=2000):
        self.enabled = enabled
        self.show_results = show_results
        self.max_result_chars = max_result_chars

    def step(self, step_number):
        if self.enabled:
            print(f"\n--- step {step_number} ---")

    def model_request(self, model, messages_count, tools_count):
        if self.enabled:
            print(f"[llm] model={model} messages={messages_count} tools={tools_count}")

    def model_response(self, assistant_message):
        if not self.enabled:
            return

        if assistant_message.tool_calls:
            print(f"[llm] requested {len(assistant_message.tool_calls)} tool call(s)")
        else:
            content = assistant_message.content or ""
            print(f"[llm] final answer chars={len(content)}")

    def tool_start(self, tool_name, arguments):
        if self.enabled:
            print(f"[tool:start] {tool_name}")
            print(json.dumps(arguments, indent=2, ensure_ascii=False))

    def tool_end(self, tool_name, result, elapsed_ms):
        if not self.enabled:
            return

        print(f"[tool:end] {tool_name} elapsed={elapsed_ms:.0f}ms")

        if not self.show_results:
            return

        text = json.dumps(result, indent=2, ensure_ascii=False)

        if len(text) > self.max_result_chars:
            text = text[:self.max_result_chars] + "\n... [truncated]"

        print(text)

    def tool_error(self, tool_name, error, elapsed_ms):
        if self.enabled:
            print(f"[tool:error] {tool_name} elapsed={elapsed_ms:.0f}ms error={error}")
