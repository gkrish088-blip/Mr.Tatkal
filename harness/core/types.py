from dataclasses import dataclass, field
from typing import Any
import inspect


@dataclass
class ToolCall:
    name: str
    arguments: dict = field(default_factory=dict)


@dataclass
class ToolResult:
    ok: bool
    data: dict = field(default_factory=dict)
    error: str | None = None
    state_hash: str = ""


@dataclass
class Decision:
    reason: str
    calls: list[ToolCall] = field(default_factory=list)
    done: bool = False
    answer: str = ""
    usage: dict = field(default_factory=dict)
    model: str = ""


class ToolRegistry:
    def __init__(self):
        self.tools = {}
        self.capture = None

    def register(self, name, function, description="", parameters=None):
        if name in self.tools:
            raise ValueError(f"Duplicate tool: {name}")
        if parameters is None:
            properties, required = {}, []
            for key, param in inspect.signature(function).parameters.items():
                if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
                    continue
                annotation = param.annotation
                if annotation is inspect.Parameter.empty and param.default is not inspect.Parameter.empty and param.default is not None:
                    annotation = type(param.default)
                kind = {int: "integer", float: "number", bool: "boolean", dict: "object", list: "array"}.get(annotation, "string")
                properties[key] = {"type": kind}
                if kind == "array":
                    properties[key]["items"] = {"type": "string"}
                if param.default is inspect.Parameter.empty:
                    required.append(key)
            parameters = {"type": "object", "properties": properties, "required": required}
        self.tools[name] = (function, description, parameters)

    def schemas(self):
        return [{"type": "function", "function": {"name": name, "description": desc, "parameters": params}}
                for name, (_, desc, params) in self.tools.items()]

    async def execute(self, call):
        try:
            fn = self.tools[call.name][0]
            result = await fn(**call.arguments)
            return result if isinstance(result, ToolResult) else ToolResult(True, result or {})
        except Exception as exc:
            return ToolResult(False, error=f"{type(exc).__name__}: {exc}")
