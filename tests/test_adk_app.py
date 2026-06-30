"""
Tests for the official Google ADK app wrapper.
"""

from adk_app.agent import app, root_agent
from adk_app import tools as adk_tools
from security import guardrails


def test_adk_root_agent_is_supply_chain_supervisor():
    assert app.name == "adk_app"
    assert root_agent.name == "supply_chain_resilience_supervisor"
    assert root_agent.model
    assert len(root_agent.tools) >= 5


def test_adk_specialist_agents_are_registered():
    names = {agent.name for agent in root_agent.sub_agents}
    assert {
        "security_agent",
        "disruption_agent",
        "demand_agent",
        "inventory_agent",
        "transport_agent",
        "evaluation_agent",
        "human_approval_agent",
        "explanation_agent",
    }.issubset(names)


def test_adk_tool_wrapper_blocks_unknown_scenario():
    result = adk_tools.run_supply_chain_recovery("unknown", "medium")
    assert result["status"] == "blocked"
    assert "allowed_scenarios" in result


def test_adk_tool_names_are_in_guardrail_allowlist():
    result = guardrails.validate_tool_request(
        "run_supply_chain_recovery",
        {"scenario_type": "demand_spike", "severity_label": "medium"},
        {"role": "planner"},
    )
    assert result["allowed"] is True
