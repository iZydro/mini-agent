import requests
from config import JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN


class Tool:
    name = "jira_my_issues"

    definition = {
        "type": "function",
        "function": {
            "name": "jira_my_issues",
            "description": (
                "Busca issues de Jira asignadas al usuario actual. "
                "Úsala para preguntas como: qué tengo asignado, bugs abiertos, "
                "tareas críticas, issues de un proyecto, o trabajo actualizado recientemente."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "project": {
                        "type": "string",
                        "description": "Clave del proyecto Jira, por ejemplo CORE. Opcional."
                    },
                    "issue_type": {
                        "type": "string",
                        "description": "Tipo de issue, por ejemplo Bug, Story, Task. Opcional."
                    },
                    "priority": {
                        "type": "string",
                        "description": "Prioridad, por ejemplo Highest, High, Medium, Low. Opcional."
                    },
                    "status_category": {
                        "type": "string",
                        "description": "Categoría de estado: To Do, In Progress o Done. Por defecto excluye Done."
                    },
                    "updated_since_days": {
                        "type": "integer",
                        "description": "Issues actualizadas en los últimos N días. Opcional."
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Número máximo de issues a devolver. Por defecto 10."
                    }
                },
                "required": []
            }
        }
    }

    def execute(
        self,
        project=None,
        issue_type=None,
        priority=None,
        status_category=None,
        updated_since_days=None,
        max_results=10
    ):
        if not JIRA_BASE_URL or not JIRA_EMAIL or not JIRA_API_TOKEN:
            raise ValueError("Faltan variables Jira en .env")

        clauses = ["assignee = currentUser()"]

        if project:
            clauses.append(f'project = "{project}"')

        if issue_type:
            clauses.append(f'issuetype = "{issue_type}"')

        if priority:
            clauses.append(f'priority = "{priority}"')

        if status_category:
            clauses.append(f'statusCategory = "{status_category}"')
        else:
            clauses.append('statusCategory != Done')

        if updated_since_days:
            clauses.append(f"updated >= -{int(updated_since_days)}d")

        jql = " AND ".join(clauses) + " ORDER BY updated DESC"

        url = f"{JIRA_BASE_URL.rstrip('/')}/rest/api/3/search/jql"

        payload = {
            "jql": jql,
            "maxResults": max_results,
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
        data = response.json()

        issues = []

        for issue in data.get("issues", []):
            fields = issue.get("fields", {})

            status = fields.get("status") or {}
            assignee = fields.get("assignee") or {}
            priority_data = fields.get("priority") or {}
            issue_type_data = fields.get("issuetype") or {}

            issues.append({
                "key": issue.get("key"),
                "url": f"{JIRA_BASE_URL.rstrip('/')}/browse/{issue.get('key')}",
                "summary": fields.get("summary"),
                "status": status.get("name"),
                "status_category": status.get("statusCategory", {}).get("name"),
                "assignee": assignee.get("displayName"),
                "priority": priority_data.get("name"),
                "type": issue_type_data.get("name"),
                "created": fields.get("created"),
                "updated": fields.get("updated")
            })

        return {
            "jql": jql,
            "count": len(issues),
            "issues": issues
        }
    