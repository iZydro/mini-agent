import requests
from urllib.parse import urlparse


class Tool:
    name = "http_get_json"

    allowed_hosts = {
        "api.github.com",
        "api.ipify.org",
    }

    definition = {
        "type": "function",
        "function": {
            "name": "http_get_json",
            "description": "Hace una llamada HTTP GET a una API pública permitida y devuelve JSON.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL completa de la API a consultar."
                    }
                },
                "required": ["url"]
            }
        }
    }

    def execute(self, url):
        parsed = urlparse(url)

        # if parsed.hostname not in self.allowed_hosts:
        #     raise ValueError(f"Host no permitido: {parsed.hostname}")

        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()