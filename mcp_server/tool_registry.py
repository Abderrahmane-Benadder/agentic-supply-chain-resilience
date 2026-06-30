"""
MCP-compatible local tool registry with schema validation and permissions.
"""

import inspect
from typing import Any, Callable, Dict, List, get_args, get_origin

from security import audit_log, guardrails


class MCPToolRegistry:
    """Registry to manage Python functions as secure MCP-style tools."""

    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self.schemas: Dict[str, Dict[str, Any]] = {}
        self.metadata: Dict[str, Dict[str, Any]] = {}

    def register(
        self,
        name: str,
        description: str,
        scopes: List[str] | None = None,
        destructive: bool = False,
        category: str = "logistics",
    ):
        """Decorator to register a tool with schema and access metadata."""
        def decorator(func: Callable):
            self.tools[name] = func
            sig = inspect.signature(func)
            parameters = {"type": "object", "properties": {}, "required": [], "additionalProperties": False}

            for param_name, param in sig.parameters.items():
                if param_name in ("self", "cls"):
                    continue

                parameters["properties"][param_name] = {
                    **self._annotation_to_schema(param.annotation),
                    "description": f"Parameter {param_name}",
                }

                if param.default == inspect.Parameter.empty:
                    parameters["required"].append(param_name)

            self.metadata[name] = {
                "scopes": scopes or ["simulator"],
                "destructive": destructive,
                "category": category,
            }
            self.schemas[name] = {
                "name": name,
                "description": description,
                "inputSchema": parameters,
                "annotations": {
                    "category": category,
                    "destructiveHint": destructive,
                    "requiredScopes": scopes or ["simulator"],
                },
            }
            return func
        return decorator

    def get_all_tool_definitions(self) -> List[Dict[str, Any]]:
        """Return list of MCP-style tool schema specifications."""
        return list(self.schemas.values())

    def call_tool(self, name: str, arguments: Dict[str, Any], context: Dict[str, Any] | None = None) -> Any:
        """Execute a registered tool after schema and permission checks."""
        if name not in self.tools:
            raise KeyError(f"Tool {name} is not registered.")

        arguments = arguments or {}
        context = context or {"role": "simulator"}

        schema_errors = self._validate_arguments(name, arguments)
        if schema_errors:
            audit_log.log_security_event("MCP_SCHEMA_VALIDATION_FAILED", {
                "tool_name": name,
                "errors": schema_errors,
                "context": context,
            }, severity="WARNING")
            raise ValueError(f"Invalid arguments for {name}: {'; '.join(schema_errors)}")

        permission = guardrails.validate_tool_request(name, arguments, context)
        if not permission["allowed"]:
            audit_log.log_security_event("MCP_TOOL_DENIED", permission, severity="WARNING")
            raise PermissionError("; ".join(permission["violations"]))

        audit_log.log_security_event("MCP_TOOL_CALL", {
            "tool_name": name,
            "context": context,
            "argument_keys": sorted(arguments.keys()),
        })
        return self.tools[name](**arguments)

    def _validate_arguments(self, name: str, arguments: Dict[str, Any]) -> List[str]:
        schema = self.schemas[name]["inputSchema"]
        errors: List[str] = []
        required = set(schema.get("required", []))
        properties = schema.get("properties", {})

        missing = sorted(required - set(arguments.keys()))
        if missing:
            errors.append(f"missing required arguments: {', '.join(missing)}")

        unknown = sorted(set(arguments.keys()) - set(properties.keys()))
        if unknown:
            errors.append(f"unknown arguments: {', '.join(unknown)}")

        for arg_name, value in arguments.items():
            if arg_name not in properties:
                continue
            expected_type = properties[arg_name].get("type")
            if not self._value_matches_json_type(value, expected_type):
                errors.append(f"argument '{arg_name}' must be {expected_type}")

        return errors

    @staticmethod
    def _value_matches_json_type(value: Any, expected_type: str) -> bool:
        if expected_type == "string":
            return isinstance(value, str)
        if expected_type == "integer":
            return isinstance(value, int) and not isinstance(value, bool)
        if expected_type == "number":
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        if expected_type == "boolean":
            return isinstance(value, bool)
        if expected_type == "array":
            return isinstance(value, list)
        if expected_type == "object":
            return isinstance(value, dict)
        return True

    @staticmethod
    def _annotation_to_schema(annotation: Any) -> Dict[str, Any]:
        origin = get_origin(annotation)
        args = get_args(annotation)

        if annotation == int:
            return {"type": "integer"}
        if annotation == float:
            return {"type": "number"}
        if annotation == bool:
            return {"type": "boolean"}
        if annotation == dict or origin == dict or origin == Dict:
            return {"type": "object"}
        if annotation == list or origin == list or origin == List:
            item_schema = {"type": "object"}
            if args and args[0] in (str, int, float, bool):
                item_schema = MCPToolRegistry._annotation_to_schema(args[0])
            return {"type": "array", "items": item_schema}
        return {"type": "string"}


registry = MCPToolRegistry()
