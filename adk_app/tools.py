"""
Official ADK tool wrappers for the supply-chain resilience engine.

The ADK agent uses these functions for tool calling. The functions delegate
all numerical logistics work to the deterministic project modules.
"""

from __future__ import annotations

import contextlib
import io
from typing import Any, Dict

import main as simulation_pipeline
from security import guardrails
from tools import data_tools


SCENARIO_LABELS = {
    "demand_spike": "Demand spike",
    "truck_breakdown": "Truck breakdown",
    "warehouse_bottleneck": "Warehouse bottleneck",
    "route_closure": "Route closure",
}

SEVERITY_LABELS = {"low", "medium", "high"}


def run_supply_chain_recovery(scenario_type: str, severity_label: str) -> Dict[str, Any]:
    """Run a complete supply-chain disruption recovery simulation.

    Args:
        scenario_type: One of demand_spike, truck_breakdown, warehouse_bottleneck, or route_closure.
        severity_label: One of low, medium, or high.

    Returns:
        A measured recovery state with KPI scorecards, policy status, and agent trace.
    """
    scenario = scenario_type.strip().lower()
    severity = severity_label.strip().lower()

    if scenario not in SCENARIO_LABELS:
        return {
            "status": "blocked",
            "reason": f"Unsupported scenario_type '{scenario_type}'.",
            "allowed_scenarios": sorted(SCENARIO_LABELS),
        }
    if severity not in SEVERITY_LABELS:
        return {
            "status": "blocked",
            "reason": f"Unsupported severity_label '{severity_label}'.",
            "allowed_severities": sorted(SEVERITY_LABELS),
        }

    security = guardrails.validate_tool_request(
        "run_supply_chain_recovery",
        {"scenario_type": scenario, "severity_label": severity},
        {"role": "simulator", "source": "adk_app"},
    )
    if not security["allowed"]:
        return {"status": "blocked", "security": security}

    captured_stdout = io.StringIO()
    with contextlib.redirect_stdout(captured_stdout):
        simulation_pipeline.run_simulation(scenario, severity)

    state = data_tools.load_session_state()
    return {
        "status": "success",
        "scenario_type": scenario,
        "scenario_label": SCENARIO_LABELS[scenario],
        "severity_label": severity,
        "session_id": state.get("session_id"),
        "final_decision": state.get("final_decision"),
        "baseline_kpis": state.get("baseline_kpis", {}),
        "disrupted_kpis": state.get("disrupted_kpis", {}),
        "recovery_kpis": state.get("recovery_kpis", {}),
        "approval": _extract_trace_output(state, "Human Approval Gate"),
        "agentic_ai_review": state.get("agentic_ai_review", {}),
        "reinforcement_learning": state.get("reinforcement_learning", {}),
        "agent_trace": state.get("agent_trace", []),
        "log_tail": captured_stdout.getvalue().splitlines()[-12:],
        "calculation_boundary": "All KPI numbers are produced by deterministic logistics tools, not by Gemini.",
    }


def get_current_recovery_state() -> Dict[str, Any]:
    """Return the most recent scenario, KPI scorecards, policy state, and trace.

    Returns:
        A JSON-serializable snapshot of the latest saved recovery run.
    """
    state = data_tools.load_session_state()
    return {
        "status": "success",
        "session_id": state.get("session_id"),
        "scenario_type": state.get("selected_scenario"),
        "severity_label": state.get("severity"),
        "final_decision": state.get("final_decision"),
        "baseline_kpis": state.get("baseline_kpis", {}),
        "disrupted_kpis": state.get("disrupted_kpis", {}),
        "recovery_kpis": state.get("recovery_kpis", {}),
        "approval": _extract_trace_output(state, "Human Approval Gate"),
        "agent_trace": state.get("agent_trace", []),
        "planner_preferences": state.get("planner_preferences", data_tools.load_planner_preferences()),
    }


def validate_logistics_dataset(name: str) -> Dict[str, Any]:
    """Validate a local logistics dataset before it is used by the agent.

    Args:
        name: Dataset name such as orders, warehouses, trucks, suppliers, or distance_matrix.

    Returns:
        Validation status and any schema or data quality errors.
    """
    security = guardrails.validate_tool_request(
        "validate_dataset",
        {"name": name},
        {"role": "planner", "source": "adk_app"},
    )
    if not security["allowed"]:
        return {"status": "blocked", "security": security}
    validation = data_tools.validate_dataset(name)
    return {"status": "success" if validation["valid"] else "failed", **validation}


def explain_agent_architecture(topic: str) -> Dict[str, Any]:
    """Return the platform's agent roles and logistics calculation boundary.

    Args:
        topic: The architecture topic the user wants explained.

    Returns:
        A structured description of the multi-agent workflow and deterministic engine.
    """
    safety = guardrails.analyze_query_safety(topic)
    if not safety["safe"]:
        return {"status": "blocked", "safety": safety}

    return {
        "status": "success",
        "topic": topic,
        "workflow": [
            "Streamlit or ADK user request",
            "SupervisorAgent coordinates the workflow",
            "SecurityAgent validates request and tool permissions",
            "DisruptionAgent identifies affected logistics entities",
            "DemandAgent evaluates customer/service exposure",
            "InventoryAgent checks feasibility and warehouse alternatives",
            "TransportAgent invokes FFD loading and route sequencing tools",
            "EvaluationAgent compares baseline, disrupted, and recovery KPIs",
            "HumanApprovalAgent enforces planner policy thresholds",
            "ExplanationAgent creates the executive recommendation",
        ],
        "adk_role": "Google ADK defines the runnable agent app, binds tools, manages sessions, and gives Gemini a tool-aware orchestration surface.",
        "llm_boundary": "Gemini coordinates, interprets risk, delegates, and explains tradeoffs.",
        "deterministic_boundary": "Inventory feasibility, FFD truck loading, route sequencing, cost, service, utilization, delay, and CO2 calculations are deterministic.",
        "agents": {
            "SupervisorAgent": "Coordinates end-to-end recovery.",
            "SecurityAgent": "Blocks unsafe prompts and unauthorized tool calls.",
            "DisruptionAgent": "Classifies the crisis and affected entities.",
            "DemandAgent": "Assesses order/customer priority impact.",
            "InventoryAgent": "Checks stock, capacity, and fallback warehouses.",
            "TransportAgent": "Builds recovery loads and routes through deterministic tools.",
            "EvaluationAgent": "Measures KPI tradeoffs.",
            "HumanApprovalAgent": "Requires planner sign-off when policy thresholds are exceeded.",
            "ExplanationAgent": "Produces the final manager-ready recommendation.",
        },
    }


def set_planner_thresholds(service_level_target_pct: float, approval_cost_increase_pct: float) -> Dict[str, Any]:
    """Update human-approval policy thresholds for future recovery runs.

    Args:
        service_level_target_pct: Minimum target service level as a percent from 0 to 100.
        approval_cost_increase_pct: Cost increase percent above baseline that requires approval.

    Returns:
        The updated planner preferences stored in memory.
    """
    if not 0 <= service_level_target_pct <= 100:
        return {"status": "blocked", "reason": "service_level_target_pct must be between 0 and 100."}
    if not 0 <= approval_cost_increase_pct <= 100:
        return {"status": "blocked", "reason": "approval_cost_increase_pct must be between 0 and 100."}

    prefs = data_tools.load_planner_preferences()
    prefs["service_level_target"] = service_level_target_pct / 100.0
    prefs["human_approval_required_if_cost_increase_above"] = approval_cost_increase_pct / 100.0
    saved = data_tools.update_planner_preferences(prefs)
    return {"status": "success" if saved else "failed", "planner_preferences": prefs}


def review_tool_permission(tool_name: str, role: str) -> Dict[str, Any]:
    """Check whether a user role may call a named tool.

    Args:
        tool_name: Tool name to check.
        role: Role name such as viewer, planner, simulator, or admin.

    Returns:
        A structured role-based authorization decision.
    """
    result = guardrails.validate_tool_request(tool_name, {}, {"role": role, "source": "adk_app"})
    return {"status": "allowed" if result["allowed"] else "blocked", "authorization": result}


def _extract_trace_output(state: Dict[str, Any], step_name: str) -> Dict[str, Any]:
    for item in state.get("agent_trace", []):
        if item.get("step") == step_name:
            return item.get("output", {})
    return {}
