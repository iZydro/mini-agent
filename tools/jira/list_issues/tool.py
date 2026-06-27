import json
import requests
from config import JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN
from core.tool_result import ToolResult
from core.api_trace import ApiTrace


def escape_jql(value):
    return str(value).replace("\\", "\\\\").replace('"', '\\"')


class Tool:
    name = "jira_list_issues"

    definition = {
        "type": "function",
        "function": {
            "name": "jira_list_issues",
            "description": (
                "Lista issues de Jira usando filtros estructurados, sin búsqueda de texto. "
                "Úsala para listar tickets de un proyecto, tickets recientes, abiertos, asignados, etc."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "project": {
                        "type": "string",
                        "description": "Clave del proyecto Jira, por ejemplo MATCH3."
                    },
                    "status_category": {
                        "type": "string",
                        "description": "Categoría de estado: To Do, In Progress o Done. Opcional."
                    },
                    "assignee": {
                        "type": "string",
                        "description": "Assignee. Usa currentUser() para el usuario actual. Opcional."
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Número máximo de issues. Por defecto 10."
                    }
                },
                "required": ["project"]
            }
        }
    }

    def execute(self, project, status_category=None, assignee=None, max_results=10):
        clauses = [f'project = "{escape_jql(project)}"']

        if status_category:
            clauses.append(f'statusCategory = "{escape_jql(status_category)}"')

        if assignee:
            if assignee == "currentUser()":
                clauses.append("assignee = currentUser()")
            else:
                clauses.append(f'assignee = "{escape_jql(assignee)}"')

        jql = " AND ".join(clauses) + " ORDER BY updated DESC"

        url = f"{JIRA_BASE_URL.rstrip('/')}/rest/api/3/search/jql"

        payload = {
            "jql": jql,
            "maxResults": min(int(max_results or 10), 25),
            "fields": [
                "summary",
                "status",
                "assignee",
                "priority",
                "issuetype",
                "updated",
                "created"
            ]
        }

        response = requests.post(
            url,
            auth=(JIRA_EMAIL, JIRA_API_TOKEN),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=20
        )

        response.raise_for_status()

        api_trace = ApiTrace.from_response(
            method="POST",
            url=url,
            response=response,
            query={
                "jql": jql,
                "maxResults": payload["maxResults"],
                "fields": payload["fields"]
            }
        ).to_dict()        

        data = response.json()

        issues = []

        for issue in data.get("issues", []):
            fields = issue.get("fields", {})
            status = fields.get("status") or {}
            assignee_data = fields.get("assignee") or {}
            priority = fields.get("priority") or {}
            issue_type = fields.get("issuetype") or {}

            issues.append({
                "key": issue.get("key"),
                "url": f"{JIRA_BASE_URL.rstrip('/')}/browse/{issue.get('key')}",
                "summary": fields.get("summary"),
                "status": status.get("name"),
                "status_category": status.get("statusCategory", {}).get("name"),
                "assignee": assignee_data.get("displayName"),
                "priority": priority.get("name"),
                "type": issue_type.get("name"),
                "created": fields.get("created"),
                "updated": fields.get("updated"),
            })

        content = {
            "jql": jql,
            "count": len(issues),
            "issues": issues
        }

        return ToolResult(
            content=json.dumps(content, ensure_ascii=False),
            ui={
                "jql": jql,
                "count": len(issues),
                "keys": [issue["key"] for issue in issues],
                "api_calls": [api_trace]
            },
            metrics={
                "issues": len(issues)
            }
        )