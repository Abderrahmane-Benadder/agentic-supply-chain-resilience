"""
Human Approval Agent.
Applies planner policy thresholds before a recovery plan can be auto-approved.
"""

from typing import Any, Dict


class HumanApprovalAgent:
    """Deterministic policy gate for human-in-the-loop logistics decisions."""

    def evaluate_policy_gate(
        self,
        baseline_kpis: Dict[str, Any],
        recovery_kpis: Dict[str, Any],
        planner_preferences: Dict[str, Any],
    ) -> Dict[str, Any]:
        baseline_cost = float(baseline_kpis.get("cost_usd", 0.0) or 0.0)
        recovery_cost = float(recovery_kpis.get("cost_usd", 0.0) or 0.0)
        recovery_otif = float(recovery_kpis.get("otif_pct", 0.0) or 0.0) / 100.0

        cost_threshold = float(
            planner_preferences.get("human_approval_required_if_cost_increase_above", 0.15)
        )
        service_target = float(planner_preferences.get("service_level_target", 0.95))

        cost_increase_pct = 0.0
        if baseline_cost > 0:
            cost_increase_pct = (recovery_cost - baseline_cost) / baseline_cost

        service_target_met = recovery_otif >= service_target
        human_approval_required = cost_increase_pct > cost_threshold or not service_target_met

        reasons = []
        if cost_increase_pct > cost_threshold:
            reasons.append("recovery cost exceeds planner approval threshold")
        if not service_target_met:
            reasons.append("recovery service level is below planner target")
        if not reasons:
            reasons.append("recovery plan is inside configured policy thresholds")

        return {
            "status": "Pending" if human_approval_required else "Auto-cleared",
            "human_approval_required": human_approval_required,
            "cost_increase_pct": round(cost_increase_pct * 100.0, 2),
            "cost_threshold_pct": round(cost_threshold * 100.0, 2),
            "service_target_pct": round(service_target * 100.0, 2),
            "service_target_met": service_target_met,
            "reasons": reasons,
        }
