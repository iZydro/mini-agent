import requests
from config import CONFLUENCE_BASE_URL, CONFLUENCE_EMAIL, CONFLUENCE_API_TOKEN
import json
from core.tool_result import ToolResult
from core.api_trace import ApiTrace


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

    def execute(self, query, space_key=None, label=None, limit=10, context=None):

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
        api_calls = []

        for strategy, cql in attempts:
            if context:
                context.info(f"Probando estrategia {strategy}", strategy=strategy)

            pages, api_trace = self.search_cql(cql, limit)
            api_trace["strategy"] = strategy
            api_calls.append(api_trace)

            all_attempts.append({
                "strategy": strategy,
                "cql": cql,
                "count": len(pages)
            })

            if pages:
                payload = {
                    "query": query,
                    "strategy": strategy,
                    "cql": cql,
                    "count": len(pages),
                    "results": pages,
                    "attempts": all_attempts
                }

                return ToolResult(
                    content=json.dumps(payload, ensure_ascii=False),
                    ui={
                        "query": query,
                        "strategy": strategy,
                        "cql": cql,
                        "count": len(pages),
                        "pages": [
                            {
                                "id": page.get("id"),
                                "title": page.get("title"),
                                "url": page.get("url"),
                                "space_key": page.get("space_key")
                            }
                            for page in pages
                        ],
                        "attempts": all_attempts,
                        "api_calls": api_calls
                    },
                    metrics={
                        "pages": len(pages),
                        "attempts": len(all_attempts)
                    }
                )

        payload = {
            "query": query,
            "count": 0,
            "results": [],
            "attempts": all_attempts
        }

        return ToolResult(
            content=json.dumps(payload, ensure_ascii=False),
            ui={
                "query": query,
                "count": 0,
                "pages": [],
                "attempts": all_attempts,
                "api_calls": api_calls
            },
            metrics={
                "pages": 0,
                "attempts": len(all_attempts)
            }
        )

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


    def search_cql(self, cql, limit, context=None, strategy=None):
        url = f"{CONFLUENCE_BASE_URL.rstrip('/')}/wiki/rest/api/search"

        params = {
            "cql": cql,
            "limit": limit,
            "expand": "content.space"
        }

        pending_trace = ApiTrace.pending(
            method="GET",
            url=url,
            query=params
        ).to_dict()

        if strategy:
            pending_trace["strategy"] = strategy

        if context:
            context.api_call_start(pending_trace)

        response = requests.get(
            url,
            auth=(CONFLUENCE_EMAIL, CONFLUENCE_API_TOKEN),
            headers={"Accept": "application/json"},
            params=params,
            timeout=20
        )

        api_trace = ApiTrace.from_response(
            method="GET",
            url=url,
            response=response,
            query=params
        ).to_dict()

        if strategy:
            api_trace["strategy"] = strategy

        if context:
            context.api_call_end(api_trace)

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

        if context:
            context.progress(
                f"{len(results)} páginas encontradas",
                count=len(results),
                strategy=strategy
            )

        return results, api_trace


    def search_cql___(self, cql, limit):
        url = f"{CONFLUENCE_BASE_URL.rstrip('/')}/wiki/rest/api/search"

        params = {
            "cql": cql,
            "limit": limit,
            "expand": "content.space"
        }

        response = requests.get(
            url,
            auth=(CONFLUENCE_EMAIL, CONFLUENCE_API_TOKEN),
            headers={"Accept": "application/json"},
            params=params,
            timeout=20
        )

        api_trace = ApiTrace.from_response(
            method="GET",
            url=url,
            response=response,
            query=params
        ).to_dict()

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

        return results, api_trace
    

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