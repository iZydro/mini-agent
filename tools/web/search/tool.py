from openai import OpenAI
from core.tool_result import ToolResult
from core.api_trace import ApiTrace


client = OpenAI()


class Tool:
    name = "web_search"

    definition = {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Busca información actual en Internet. "
                "Úsala cuando el usuario pregunte por datos recientes, noticias, precios, "
                "documentación actualizada, versiones de software, APIs, eventos o cualquier información "
                "que pueda haber cambiado."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Consulta de búsqueda web."
                    }
                },
                "required": ["query"]
            }
        }
    }

    def execute(self, query):
        response = client.responses.create(
            model="gpt-5.5",
            tools=[
                {
                    "type": "web_search"
                }
            ],
            input=(
                "Busca en la web y responde de forma breve y estructurada. "
                "Incluye enlaces/citas si están disponibles.\n\n"
                f"Consulta: {query}"
            )
        )

        # print("=" * 80)
        # print(response.model_dump_json(indent=2))
        # print("=" * 80)

        searches = []
        opened_pages = []
        web_calls = []
        citations = []

        for item in response.output:
            if item.type == "web_search_call":
                action = item.action

                if action.type == "search":
                    web_calls.append({
                        "type": "search",
                        "query": getattr(action, "query", None),
                        "queries": getattr(action, "queries", []) or [],
                        "status": item.status
                    })

                elif action.type == "open_page":
                    web_calls.append({
                        "type": "open_page",
                        "url": getattr(action, "url", None),
                        "status": item.status
                    })

            elif item.type == "message":
                for content in item.content:
                    for annotation in getattr(content, "annotations", []) or []:
                        if annotation.type == "url_citation":
                            citations.append({
                                "title": annotation.title,
                                "url": annotation.url
                            })

        return ToolResult(
            content=response.output_text,
            ui={
                "query": query,
                "web_calls": web_calls,
                "citations": citations
            },
            metrics={
                "search_requests": (response.tool_usage or {})
                    .get("web_search", {})
                    .get("num_requests", 0)
            }
        )
    