from openai import OpenAI

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

        print("=" * 80)
        print(response.model_dump_json(indent=2))
        print("=" * 80)

        return {
            "query": query,
            "answer": response.output_text
        }