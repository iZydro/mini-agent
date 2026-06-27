from dataclasses import dataclass, field
from urllib.parse import urlparse


SENSITIVE_KEYS = {
    "authorization",
    "cookie",
    "token",
    "api_key",
    "apikey",
    "password",
    "secret",
    "key",
}


def sanitize_value(key, value):
    key_lower = str(key).lower()

    if any(sensitive in key_lower for sensitive in SENSITIVE_KEYS):
        return "***"

    return value


def sanitize_dict(data):
    if not data:
        return {}

    return {
        key: sanitize_value(key, value)
        for key, value in data.items()
    }


@dataclass
class ApiTrace:
    method: str
    url: str
    query: dict = field(default_factory=dict)
    status_code: int | None = None
    elapsed_ms: int | None = None

    @classmethod
    def from_response(cls, method, url, response, query=None):
        return cls(
            method=method,
            url=url,
            query=query or {},
            status_code=response.status_code,
            elapsed_ms=round(response.elapsed.total_seconds() * 1000)
        )

    def to_dict(self):
        parsed = urlparse(self.url)

        return {
            "method": self.method.upper(),
            "scheme": parsed.scheme,
            "host": parsed.netloc,
            "path": parsed.path,
            "query": sanitize_dict(self.query),
            "status_code": self.status_code,
            "elapsed_ms": self.elapsed_ms
        }