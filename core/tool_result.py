from dataclasses import dataclass, field


@dataclass
class ToolResult:
    content: str
    ui: dict = field(default_factory=dict)
    metrics: dict = field(default_factory=dict)