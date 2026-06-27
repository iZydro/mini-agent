from openai import OpenAI
from core.tool_result import ToolResult

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
        citations = []

        for item in response.output:
            if item.type == "web_search_call":
                action = item.action

                if action.type == "search":
                    searches.extend(getattr(action, "queries", []) or [])

                elif action.type == "open_page":
                    opened_pages.append({
                        "url": getattr(action, "url", None)
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
                "searches": searches,
                "opened_pages": opened_pages,
                "citations": citations
            },
            metrics={
                "search_requests": (response.tool_usage or {})
                    .get("web_search", {})
                    .get("num_requests", 0)
            }
        )
    