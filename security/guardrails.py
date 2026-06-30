"""
Guardrails for input safety, tool authorization, and recovery-plan compliance.
"""

import re
from typing import Any, Dict, List, Tuple


ALLOWED_SCENARIOS = {"demand_spike", "truck_breakdown", "warehouse_bottleneck", "route_closure"}
ALLOWED_DATASETS = {"orders", "warehouses", "trucks", "suppliers", "distance_matrix"}

ROLE_TOOL_ALLOWLIST = {
    "viewer": {"validate_dataset", "compare_baseline_disrupted_recovery", "generate_manager_summary"},
    "planner": {
        "validate_dataset",
        "validate_logistics_dataset",
        "get_current_recovery_state",
        "explain_agent_architecture",
        "set_planner_thresholds",
        "review_tool_permission",
        "run_supply_chain_recovery",
        "check_inventory_feasibility",
        "assign_orders_to_warehouses",
        "build_truckloads_ffd",
        "sequence_route_nearest_neighbor",
        "calculate_transport_kpis",
        "compare_baseline_disrupted_recovery",
        "generate_manager_summary",
    },
    "simulator": {
        "validate_dataset",
        "validate_logistics_dataset",
        "get_current_recovery_state",
        "explain_agent_architecture",
        "set_planner_thresholds",
        "review_tool_permission",
        "run_supply_chain_recovery",
        "simulate_disruption",
        "check_inventory_feasibility",
        "assign_orders_to_warehouses",
        "build_truckloads_ffd",
        "sequence_route_nearest_neighbor",
        "calculate_transport_kpis",
        "compare_baseline_disrupted_recovery",
        "generate_manager_summary",
    },
    "admin": {"*"},
}

PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"reveal\s+(the\s+)?(system|developer)\s+prompt",
    r"override[_\s-]?security",
    r"bypass\s+(guardrails|security|policy)",
    r"act\s+as\s+(root|admin|developer)",
    r"disable\s+(audit|logging|guardrails)",
]

COMMAND_INJECTION_PATTERNS = [
    r"\brm\s+-rf\b",
    r"\bdel\s+/[sfq]\b",
    r"\bdrop\s+table\b",
    r"\btruncate\s+table\b",
    r"\bsystem\.exit\b",
    r"\beval\s*\(",
    r"\bexec\s*\(",
    r"<script\b",
    r"\bpowershell\b.*\bremove-item\b",
]

SECRET_PATTERNS = [
    r"AIza[0-9A-Za-z\-_]{20,}",
    r"sk-[A-Za-z0-9]{20,}",
    r"-----BEGIN\s+(RSA|OPENSSH|EC)\s+PRIVATE\s+KEY-----",
    r"\b(?:password|api[_-]?key|secret|token)\s*[:=]\s*['\"]?[^'\"\s]{8,}",
]

PII_PATTERNS = [
    r"\b\d{3}-\d{2}-\d{4}\b",
    r"\b(?:\+?\d[\d\s().-]{8,}\d)\b",
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
]


def analyze_query_safety(query: str) -> Dict[str, Any]:
    """Return a structured safety assessment for an incoming natural-language request."""
    query_text = query or ""
    lowered = query_text.lower()
    findings: List[Dict[str, str]] = []
    risk_score = 0

    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, lowered, flags=re.IGNORECASE):
            findings.append({"type": "prompt_injection", "pattern": pattern})
            risk_score += 35

    for pattern in COMMAND_INJECTION_PATTERNS:
        if re.search(pattern, lowered, flags=re.IGNORECASE):
            findings.append({"type": "command_or_sql_injection", "pattern": pattern})
            risk_score += 45

    for pattern in SECRET_PATTERNS:
        if re.search(pattern, query_text, flags=re.IGNORECASE):
            findings.append({"type": "secret_or_credential", "pattern": pattern})
            risk_score += 40

    for pattern in PII_PATTERNS:
        if re.search(pattern, query_text, flags=re.IGNORECASE):
            findings.append({"type": "possible_pii", "pattern": pattern})
            risk_score += 10

    if len(query_text) > 2500:
        findings.append({"type": "oversized_prompt", "pattern": "length>2500"})
        risk_score += 20

    blocked = any(finding["type"] in {"prompt_injection", "command_or_sql_injection", "secret_or_credential"} for finding in findings)
    return {
        "safe": not blocked,
        "risk_score": min(risk_score, 100),
        "findings": findings,
        "action": "block" if blocked else ("warn" if findings else "allow"),
    }


def is_query_safe(query: str) -> bool:
    """Backward-compatible boolean safety check."""
    return bool(analyze_query_safety(query)["safe"])


def validate_tool_request(tool_name: str, arguments: Dict[str, Any], context: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Validate role permissions and high-risk tool arguments before execution."""
    context = context or {}
    role = context.get("role", "simulator")
    allowed_tools = ROLE_TOOL_ALLOWLIST.get(role, set())
    violations: List[str] = []

    if "*" not in allowed_tools and tool_name not in allowed_tools:
        violations.append(f"role '{role}' is not allowed to call tool '{tool_name}'")

    if tool_name == "simulate_disruption":
        scenario_type = str(arguments.get("scenario_type", ""))
        if scenario_type not in ALLOWED_SCENARIOS:
            violations.append(f"scenario_type '{scenario_type}' is not allowed")
        try:
            severity = float(arguments.get("severity", 0.35))
            if severity < 0.0 or severity > 1.0:
                violations.append("severity must be between 0.0 and 1.0")
        except (TypeError, ValueError):
            violations.append("severity must be numeric")

    if tool_name == "validate_dataset":
        dataset_name = str(arguments.get("name", ""))
        if dataset_name not in ALLOWED_DATASETS:
            violations.append(f"dataset '{dataset_name}' is not allowed")

    for key, value in arguments.items():
        if isinstance(value, str):
            safety = analyze_query_safety(value)
            if not safety["safe"]:
                violations.append(f"argument '{key}' failed safety check")

    return {
        "allowed": len(violations) == 0,
        "role": role,
        "tool_name": tool_name,
        "violations": violations,
    }


def verify_structural_plan(plan_actions: List[Dict[str, Any]]) -> bool:
    """Verify that generated plan lists have all mandatory keys."""
    mandatory_keys = {"type", "cost_usd", "hours_saved"}
    for action in plan_actions:
        if not mandatory_keys.issubset(action.keys()):
            return False
    return True


def evaluate_plan_policy(plan_actions: List[Dict[str, Any]], evaluation_result: Dict[str, Any], max_budget_limit: float) -> Dict[str, Any]:
    """Return structured output-policy assessment for a proposed recovery plan."""
    violations: List[str] = []
    warnings: List[str] = []

    if not verify_structural_plan(plan_actions):
        violations.append("plan action schema is incomplete")

    total_cost = float(evaluation_result.get("total_recovery_cost_usd", evaluation_result.get("total_cost_usd", 0.0)) or 0.0)
    if total_cost > max_budget_limit:
        violations.append(f"plan cost {total_cost:.2f} exceeds hard budget limit {max_budget_limit:.2f}")

    for index, action in enumerate(plan_actions):
        cost = float(action.get("cost_usd", 0.0) or 0.0)
        hours_saved = float(action.get("hours_saved", 0.0) or 0.0)
        if cost < 0:
            violations.append(f"action {index} has negative cost")
        if hours_saved < 0:
            warnings.append(f"action {index} reports negative hours_saved")

    return {
        "approved": len(violations) == 0,
        "violations": violations,
        "warnings": warnings,
        "total_cost": total_cost,
    }
