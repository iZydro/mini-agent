import json


class ConsoleListener:
    def __init__(self, enabled=True, show_results=False, max_result_chars=2000):
        self.enabled = enabled
        self.show_results = show_results
        self.max_result_chars = max_result_chars

    def on_event(self, event):
        if not self.enabled:
            return

        event_type = event.get("type")

        if event_type == "agent_step":
            print(f"\n--- step {event['step']} ---")

        elif event_type == "llm_request":
            print(
                f"[llm] model={event['model']} "
                f"messages={event['messages_count']} "
                f"tools={event['tools_count']}"
            )

        elif event_type == "llm_tool_calls":
            print(f"[llm] requested {event['count']} tool call(s)")

        elif event_type == "llm_final_answer":
            print(f"[llm] final answer chars={event['chars']}")

        elif event_type == "tool_start":
            print(f"[tool:start] {event['tool']}")
            print(json.dumps(event.get("arguments", {}), indent=2, ensure_ascii=False))

        elif event_type == "tool_end":
            print(f"[tool:end] {event['tool']} elapsed={event['elapsed_ms']:.0f}ms")

            if self.show_results:
                text = json.dumps(event.get("result"), indent=2, ensure_ascii=False)
                if len(text) > self.max_result_chars:
                    text = text[:self.max_result_chars] + "\n... [truncated]"
                print(text)

        elif event_type == "tool_error":
            print(
                f"[tool:error] {event['tool']} "
                f"elapsed={event['elapsed_ms']:.0f}ms "
                f"error={event['error']}"
            )