"""
Tests for the MCP-compatible local tool registry security controls.
"""

import pytest

from mcp_server.server import registry


def test_mcp_tool_schemas_include_security_annotations():
    tools = registry.get_all_tool_definitions()
    simulate = next(tool for tool in tools if tool["name"] == "simulate_disruption")

    assert simulate["annotations"]["destructiveHint"] is True
    assert "simulator" in simulate["annotations"]["requiredScopes"]
    assert simulate["inputSchema"]["additionalProperties"] is False


def test_mcp_tool_call_denies_wrong_role():
    with pytest.raises(PermissionError):
        registry.call_tool(
            "simulate_disruption",
            {"scenario_type": "route_closure", "severity": 0.3},
            context={"role": "viewer"},
        )


def test_mcp_tool_call_validates_schema():
    with pytest.raises(ValueError):
        registry.call_tool(
            "validate_dataset",
            {"name": "orders", "unexpected": "value"},
            context={"role": "viewer"},
        )


def test_mcp_tool_call_allows_safe_viewer_tool():
    result = registry.call_tool(
        "validate_dataset",
        {"name": "orders"},
        context={"role": "viewer"},
    )
    assert result["valid"] is True
