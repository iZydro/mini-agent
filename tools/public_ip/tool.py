import requests
import json
from core.tool_result import ToolResult

class Tool:
    name = "get_public_ip"

    definition = {
        "type": "function",
        "function": {
            "name": "get_public_ip",
            "description": "Obtiene la IP pública actual usando una API externa.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }

    def execute(self):
        r = requests.get("https://api.ipify.org?format=json", timeout=10)
        r.raise_for_status()
    
        data = r.json()

        return ToolResult(
            content=json.dumps(data, ensure_ascii=False),
            ui={
                "ip": data.get("ip")
            },
            metrics={}
        )
    