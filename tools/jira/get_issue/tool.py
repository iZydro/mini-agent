import re
import requests
from config import JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN
import json
from core.tool_result import ToolResult


def adf_to_text(node):
    if not node:
        return ""

    if isinstance(node, str):
        return node

    if isinstance(node, list):
        return "".join(adf_to_text(child) for child in node)

    if not isinstance(node, dict):
        return ""

    node_type = node.get("type")
    text = node.get("text", "")

    if text:
        return text

    content = node.get("content", [])
    inner = adf_to_text(content)

    if node_type in ["paragraph", "heading"]:
        return inner + "\n"

    if node_type == "bulletList":
        return inner + "\n"

    if node_type == "orderedList":
        return inner + "\n"

    if node_type == "listItem":
        return "- " + inner.strip() + "\n"

    if node_type == "hardBreak":
        return "\n"

    return inner


def clean_text(value):
    if not value:
        return ""

    text = adf_to_text(value) if isinstance(value, dict) else str(value)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class Tool:
    name = "jira_get_issue"

    definition = {
        "type": "function",
        "function": {
            "name": "jira_get_issue",
            "description": (
                "Obtiene el detalle de una issue de Jira por clave, incluyendo descripción, "
                "comentarios recientes, labels, componentes y enlaces."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Clave de la issue, por ejemplo CORE-123."
                    },
                    "max_comments": {
                        "type": "integer",
                        "description": "Número máximo de comentarios recientes. Por defecto 5."
                    }
                },
                "required": ["key"]
            }
        }
    }

    def execute(self, key, max_comments=5):
        if not JIRA_BASE_URL or not JIRA_EMAIL or not JIRA_API_TOKEN:
            raise ValueError("Faltan variables Jira en .env")

        issue = self.get_issue(key)
        comments = self.get_comments(key, max_comments)

        fields = issue.get("fields", {})

        status = fields.get("status") or {}
        assignee = fields.get("assignee") or {}
        reporter = fields.get("reporter") or {}
        priority = fields.get("priority") or {}
        issue_type = fields.get("issuetype") or {}


        result = {
            "key": issue.get("key"),
            "url": f"{JIRA_BASE_URL.rstrip('/')}/browse/{issue.get('key')}",
            "summary": fields.get("summary"),
            "description": clean_text(fields.get("description"))[:12000],
            "status": status.get("name"),
            "status_category": status.get("statusCategory", {}).get("name"),
            "assignee": assignee.get("displayName"),
            "reporter": reporter.get("displayName"),
            "priority": priority.get("name"),
            "type": issue_type.get("name"),
            "labels": fields.get("labels") or [],
            "components": [
                component.get("name")
                for component in fields.get("components", [])
            ],
            "created": fields.get("created"),
            "updated": fields.get("updated"),
            "comments": comments
        }

        return ToolResult(
            content=json.dumps(result, ensure_ascii=False),
            ui={
                "key": result["key"],
                "summary": result["summary"],
                "url": result["url"],
                "comments": len(comments),
                "status": result["status"]
            },
            metrics={
                "comments": len(comments),
                "description_chars": len(result["description"] or "")
            }
        )


    def get_issue(self, key):
        url = f"{JIRA_BASE_URL.rstrip('/')}/rest/api/3/issue/{key}"

        response = requests.get(
            url,
            auth=(JIRA_EMAIL, JIRA_API_TOKEN),
            headers={
                "Accept": "application/json"
            },
            params={
                "fields": ",".join([
                    "summary",
                    "description",
                    "status",
                    "assignee",
                    "reporter",
                    "priority",
                    "issuetype",
                    "labels",
                    "components",
                    "updated",
                    "created"
                ])
            },
            timeout=20
        )

        response.raise_for_status()
        return response.json()

    def get_comments(self, key, max_comments):
        url = f"{JIRA_BASE_URL.rstrip('/')}/rest/api/3/issue/{key}/comment"

        response = requests.get(
            url,
            auth=(JIRA_EMAIL, JIRA_API_TOKEN),
            headers={
                "Accept": "application/json"
            },
            params={
                "maxResults": min(int(max_comments or 5), 20),
                "orderBy": "-created"
            },
            timeout=20
        )

        response.raise_for_status()
        data = response.json()

        comments = []

        for comment in data.get("comments", []):
            author = comment.get("author") or {}

            comments.append({
                "author": author.get("displayName"),
                "created": comment.get("created"),
                "updated": comment.get("updated"),
                "body": clean_text(comment.get("body"))[:4000]
            })

        return comments