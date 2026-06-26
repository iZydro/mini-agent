import requests
from config import CONFLUENCE_BASE_URL, CONFLUENCE_EMAIL, CONFLUENCE_API_TOKEN


def escape_cql_value(value):
    return str(value).replace("\\", "\\\\").replace('"', '\\"')


class Tool:
    name = "confluence_search"

    definition = {
        "type": "function",
        "function": {
            "name": "confluence_search",
            "description": (
                "Busca contenido en Confluence de forma flexible usando texto, espacio y label opcionales. "
                "Úsala para encontrar documentación aunque el usuario no sepa el título exacto."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Texto libre a buscar, por ejemplo 'bonus cash', 'payments', 'Jira onboarding'."
                    },
                    "space_key": {
                        "type": "string",
                        "description": "Clave del espacio de Confluence, opcional."
                    },
                    "label": {
                        "type": "string",
                        "description": "Label de Confluence, opcional."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Número máximo de resultados. Por defecto 10."
                    }
                },
                "required": ["query"]
            }
        }
    }

    def execute(self, query, space_key=None, label=None, limit=10):
        if not CONFLUENCE_BASE_URL or not CONFLUENCE_EMAIL or not CONFLUENCE_API_TOKEN:
            raise ValueError("Faltan variables de Confluence en .env")

        limit = min(int(limit or 10), 25)

        attempts = [
            ("siteSearch", self.build_cql("siteSearch", query, space_key, label)),
            ("title + text words", self.build_mixed_cql(query, space_key, label)),
            ("text", self.build_cql("text", query, space_key, label)),
            ("title", self.build_title_cql(query, space_key, label)),
        ]

        all_attempts = []

        for strategy, cql in attempts:
            result = self.search_cql(cql, limit)

            all_attempts.append({
                "strategy": strategy,
                "cql": cql,
                "count": len(result)
            })

            if result:
                return {
                    "query": query,
                    "strategy": strategy,
                    "cql": cql,
                    "count": len(result),
                    "results": result,
                    "attempts": all_attempts
                }

        return {
            "query": query,
            "count": 0,
            "results": [],
            "attempts": all_attempts
        }

    def build_cql(self, field, query, space_key=None, label=None):
        clauses = [
            "type = page",
            f'{field} ~ "{escape_cql_value(query)}"'
        ]

        if space_key:
            clauses.append(f'space = "{escape_cql_value(space_key)}"')

        if label:
            clauses.append(f'label = "{escape_cql_value(label)}"')

        return " AND ".join(clauses) + " ORDER BY lastmodified DESC"

    def build_title_cql(self, query, space_key=None, label=None):
        words = [
            word.strip()
            for word in query.split()
            if len(word.strip()) >= 3
        ]

        if not words:
            words = [query]

        title_clauses = [
            f'title ~ "{escape_cql_value(word)}*"'
            for word in words[:4]
        ]

        clauses = [
            "type = page",
            "(" + " OR ".join(title_clauses) + ")"
        ]

        if space_key:
            clauses.append(f'space = "{escape_cql_value(space_key)}"')

        if label:
            clauses.append(f'label = "{escape_cql_value(label)}"')

        return " AND ".join(clauses) + " ORDER BY lastmodified DESC"

    def search_cql(self, cql, limit):
        url = f"{CONFLUENCE_BASE_URL.rstrip('/')}/wiki/rest/api/search"

        response = requests.get(
            url,
            auth=(CONFLUENCE_EMAIL, CONFLUENCE_API_TOKEN),
            headers={
                "Accept": "application/json"
            },
            params={
                "cql": cql,
                "limit": limit,
                "expand": "content.space"
            },
            timeout=20
        )

        response.raise_for_status()
        data = response.json()

        results = []

        for item in data.get("results", []):
            content = item.get("content") or {}
            space = content.get("space") or {}
            links = content.get("_links") or {}
            webui = links.get("webui")

            results.append({
                "id": content.get("id"),
                "title": content.get("title"),
                "type": content.get("type"),
                "space_key": space.get("key"),
                "space_name": space.get("name"),
                "excerpt": item.get("excerpt"),
                "url": f"{CONFLUENCE_BASE_URL.rstrip('/')}/wiki{webui}" if webui else None
            })

        return results
    
    def build_mixed_cql(self, query, space_key=None, label=None):
        words = [
            word.strip()
            for word in query.split()
            if len(word.strip()) >= 3
        ]

        if len(words) < 2:
            return self.build_cql("siteSearch", query, space_key, label)

        first = escape_cql_value(words[0])
        rest = words[1:]

        clauses = [
            "type = page",
            f'title ~ "{first}*"',
        ]

        for word in rest[:4]:
            clauses.append(f'text ~ "{escape_cql_value(word)}*"')

        if space_key:
            clauses.append(f'space = "{escape_cql_value(space_key)}"')

        if label:
            clauses.append(f'label = "{escape_cql_value(label)}"')

        return " AND ".join(clauses) + " ORDER BY lastmodified DESC"    