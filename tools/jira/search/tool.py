import requests
from config import JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN


def escape_jql(value):
    return str(value).replace("\\", "\\\\").replace('"', '\\"')


class Tool:
    name = "jira_search"

    definition = {
        "type": "function",
        "function": {
            "name": "jira_search",
            "description": (
                "Busca issues de Jira por texto libre en summary, description y texto general. "
                "Úsala cuando el usuario quiera encontrar tickets sobre un tema, bug, feature o palabra clave."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Texto libre a buscar, por ejemplo 'bonus cash', 'solitaire rules', 'facebook ads'."
                    },
                    "project": {
                        "type": "string",
                        "description": "Clave del proyecto Jira, opcional."
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Número máximo de issues. Por defecto 10."
                    }
                },
                "required": ["query"]
            }
        }
    }

    def execute(self, query, project=None, max_results=10):
        if not JIRA_BASE_URL or not JIRA_EMAIL or not JIRA_API_TOKEN:
            raise ValueError("Faltan variables Jira en .env")

        max_results = min(int(max_results or 10), 25)

        attempts = [
            ("text phrase", self.build_text_phrase_jql(query, project)),
            ("summary words", self.build_summary_words_jql(query, project)),
            ("summary or description words", self.build_summary_description_words_jql(query, project)),
        ]

        all_attempts = []

        for strategy, jql in attempts:
            issues = self.search_jql(jql, max_results)

            all_attempts.append({
                "strategy": strategy,
                "jql": jql,
                "count": len(issues)
            })

            if issues:
                return {
                    "query": query,
                    "strategy": strategy,
                    "jql": jql,
                    "count": len(issues),
                    "issues": issues,
                    "attempts": all_attempts
                }

        return {
            "query": query,
            "count": 0,
            "issues": [],
            "attempts": all_attempts
        }

    def add_project_clause(self, clauses, project):
        if project:
            clauses.append(f'project = "{escape_jql(project)}"')

    def build_text_phrase_jql(self, query, project):
        clauses = []
        self.add_project_clause(clauses, project)
        clauses.append(f'text ~ "{escape_jql(query)}"')
        return " AND ".join(clauses) + " ORDER BY updated DESC"

    def build_summary_words_jql(self, query, project):
        words = self.get_words(query)

        word_clauses = [
            f'summary ~ "{escape_jql(word)}*"'
            for word in words
        ]

        clauses = []
        self.add_project_clause(clauses, project)
        clauses.append("(" + " OR ".join(word_clauses) + ")")

        return " AND ".join(clauses) + " ORDER BY updated DESC"

    def build_summary_description_words_jql(self, query, project):
        words = self.get_words(query)

        word_clauses = []

        for word in words:
            escaped = escape_jql(word)
            word_clauses.append(f'summary ~ "{escaped}*"')
            word_clauses.append(f'description ~ "{escaped}*"')

        clauses = []
        self.add_project_clause(clauses, project)
        clauses.append("(" + " OR ".join(word_clauses) + ")")

        return " AND ".join(clauses) + " ORDER BY updated DESC"

    def get_words(self, query):
        words = [
            word.strip()
            for word in query.split()
            if len(word.strip()) >= 3
        ]

        return words[:5] or [query]

    def search_jql(self, jql, max_results):
        url = f"{JIRA_BASE_URL.rstrip('/')}/rest/api/3/search/jql"

        payload = {
            "jql": jql,
            "maxResults": max_results,
            "fields": [
                "summary",
                "status",
                "assignee",
                "reporter",
                "priority",
                "issuetype",
                "labels",
                "components",
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
            reporter = fields.get("reporter") or {}
            priority = fields.get("priority") or {}
            issue_type = fields.get("issuetype") or {}

            issues.append({
                "key": issue.get("key"),
                "url": f"{JIRA_BASE_URL.rstrip('/')}/browse/{issue.get('key')}",
                "summary": fields.get("summary"),
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
            })

        return issues