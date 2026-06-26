import re
import html
import requests
from config import CONFLUENCE_BASE_URL, CONFLUENCE_EMAIL, CONFLUENCE_API_TOKEN


def html_to_text(value):
    if not value:
        return ""

    text = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)
    text = re.sub(r"</p\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</h[1-6]\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)

    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


class Tool:
    name = "confluence_get_page"

    definition = {
        "type": "function",
        "function": {
            "name": "confluence_get_page",
            "description": (
                "Obtiene el contenido de una página de Confluence a partir de su page_id. "
                "Úsala después de buscar páginas o cuando el usuario dé un ID de página."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "page_id": {
                        "type": "string",
                        "description": "ID numérico de la página de Confluence."
                    }
                },
                "required": ["page_id"]
            }
        }
    }

    def execute(self, page_id):
        if not CONFLUENCE_BASE_URL or not CONFLUENCE_EMAIL or not CONFLUENCE_API_TOKEN:
            raise ValueError("Faltan variables de Confluence en .env")

        url = f"{CONFLUENCE_BASE_URL.rstrip('/')}/wiki/api/v2/pages/{page_id}"

        response = requests.get(
            url,
            auth=(CONFLUENCE_EMAIL, CONFLUENCE_API_TOKEN),
            headers={
                "Accept": "application/json"
            },
            params={
                "body-format": "storage"
            },
            timeout=20
        )

        response.raise_for_status()
        page = response.json()

        storage = page.get("body", {}).get("storage", {})
        raw_html = storage.get("value", "")
        text = html_to_text(raw_html)

        links = page.get("_links", {})
        webui = links.get("webui")

        return {
            "id": page.get("id"),
            "title": page.get("title"),
            "status": page.get("status"),
            "spaceId": page.get("spaceId"),
            "createdAt": page.get("createdAt"),
            "url": f"{CONFLUENCE_BASE_URL.rstrip('/')}{webui}" if webui else None,
            "text": text[:12000]
        }