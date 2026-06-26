import requests
from config import CONFLUENCE_BASE_URL, CONFLUENCE_EMAIL, CONFLUENCE_API_TOKEN


class Tool:
    name = "confluence_search_pages"

    definition = {
        "type": "function",
        "function": {
            "name": "confluence_search_pages",
            "description": (
                "Busca páginas de Confluence por texto en el título. "
                "Úsala cuando el usuario quiera encontrar documentación, páginas, specs o notas."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Texto a buscar en el título de la página."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Número máximo de resultados. Por defecto 10."
                    }
                },
                "required": ["title"]
            }
        }
    }

    def execute(self, title, limit=10):
        if not CONFLUENCE_BASE_URL or not CONFLUENCE_EMAIL or not CONFLUENCE_API_TOKEN:
            raise ValueError("Faltan variables de Confluence en .env")

        url = f"{CONFLUENCE_BASE_URL.rstrip('/')}/wiki/api/v2/pages"

        response = requests.get(
            url,
            auth=(CONFLUENCE_EMAIL, CONFLUENCE_API_TOKEN),
            headers={
                "Accept": "application/json"
            },
            params={
                "title": title,
                "limit": limit
            },
            timeout=20
        )

        response.raise_for_status()
        data = response.json()

        pages = []

        for page in data.get("results", []):
            links = page.get("_links", {})
            webui = links.get("webui")

            pages.append({
                "id": page.get("id"),
                "title": page.get("title"),
                "status": page.get("status"),
                "spaceId": page.get("spaceId"),
                "createdAt": page.get("createdAt"),
                "url": f"{CONFLUENCE_BASE_URL.rstrip('/')}{webui}" if webui else None,
            })

        return {
            "query": title,
            "count": len(pages),
            "pages": pages
        }
