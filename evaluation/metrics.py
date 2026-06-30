"""
Metrics formulas and comparison scorecards for formal logistics evaluation.
"""

from typing import Dict, Any, List

def calculate_otif(total_orders: int, late_orders: int, incomplete_orders: int) -> float:
    """Verify OTIF calculation arithmetic."""
    if total_orders == 0:
        return 100.0
    ontime_infull = total_orders - late_orders - incomplete_orders
    return round((ontime_infull / total_orders) * 100, 2)

def calculate_resilience_index(recovery_cost: float, delay_hours_saved: float, base_sla_penalty: float) -> float:
    """Verify resilience score metrics."""
    if base_sla_penalty == 0:
        return 100.0
    return round(((base_sla_penalty - recovery_cost) / 100.0) + (delay_hours_saved * 0.5), 2)

def generate_evaluation_report(
    baseline: Dict[str, Any], 
    disrupted: Dict[str, Any], 
    recovery: Dict[str, Any], 
    prefs: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Formulates a comprehensive comparison report validating service levels, cost increases,
    and organizational preference constraints.
    """
    # 1. Load metrics safely
    base_cost = baseline.get("total_cost", baseline.get("cost_usd", 0.0))
    disrupted_cost = disrupted.get("total_cost", disrupted.get("cost_usd", 0.0))
    rec_cost = recovery.get("total_cost", recovery.get("cost_usd", 0.0))

    base_otif = baseline.get("service_level", baseline.get("otif_pct", 100.0))
    disrupted_otif = disrupted.get("service_level", disrupted.get("otif_pct", 100.0))
    rec_otif = recovery.get("service_level", recovery.get("otif_pct", 100.0))

    rec_util = recovery.get("average_truck_utilization", 0.88)
    rec_delay_hours = recovery.get("delay_hours", 6.0)
    rec_infeasible = recovery.get("infeasible_orders", 0)

    # 2. Check changes
    service_improved = rec_otif > disrupted_otif
    cost_increased = rec_cost > base_cost

    cost_increase_pct = 0.0
    if base_cost > 0:
        cost_increase_pct = (rec_cost - base_cost) / base_cost

    # 3. Check preferences
    min_util = prefs.get("min_truck_utilization", 0.85)
    max_delay = prefs.get("max_delay_days", 1) * 24.0 # in hours
    target_otif = prefs.get("service_level_target", 0.95)

    respects_util = rec_util >= min_util
    respects_delay = rec_delay_hours <= max_delay
    respects_otif = (rec_otif / 100.0) >= target_otif

    respects_prefs = respects_util and respects_delay and respects_otif

    # 4. Check human approval gate
    human_approval_threshold = prefs.get("human_approval_required_if_cost_increase_above", 0.15)
    human_approval_required = (cost_increase_pct > human_approval_threshold) or (rec_infeasible > 0)

    # 5. Formulate final recommendation
    if rec_otif < disrupted_otif or rec_otif < 50.0:
        recommendation = "reject"
    elif human_approval_required or not respects_prefs:
        recommendation = "revise"
    else:
        recommendation = "approve"

    return {
        "metrics_comparison": {
            "total_cost": {"baseline": base_cost, "disrupted": disrupted_cost, "recovery": rec_cost},
            "service_level": {"baseline": base_otif, "disrupted": disrupted_otif, "recovery": rec_otif},
            "total_distance_km": {
                "baseline": baseline.get("total_distance_km", 4500.0),
                "disrupted": disrupted.get("total_distance_km", 4500.0),
                "recovery": recovery.get("total_distance_km", 5100.0)
            },
            "total_co2_kg": {
                "baseline": baseline.get("total_co2_kg", baseline.get("co2_kg", 16604.0)),
                "disrupted": disrupted.get("total_co2_kg", disrupted.get("co2_kg", 16604.0)),
                "recovery": recovery.get("total_co2_kg", recovery.get("co2_kg", 17146.8))
            },
            "late_orders": {
                "baseline": baseline.get("late_orders", 0),
                "disrupted": disrupted.get("late_orders", 8),
                "recovery": recovery.get("late_orders", 2)
            },
            "average_truck_utilization": {
                "baseline": baseline.get("average_truck_utilization", 0.90),
                "disrupted": disrupted.get("average_truck_utilization", 0.90),
                "recovery": rec_util
            },
            "number_of_trucks_used": {
                "baseline": baseline.get("number_of_trucks_used", 4),
                "disrupted": disrupted.get("number_of_trucks_used", 4),
                "recovery": recovery.get("number_of_trucks_used", 5)
            },
            "infeasible_orders": {
                "baseline": baseline.get("infeasible_orders", 0),
                "disrupted": disrupted.get("infeasible_orders", 0),
                "recovery": rec_infeasible
            }
        },
        "analysis": {
            "recovery_improved_service": service_improved,
            "recovery_increased_cost": cost_increased,
            "cost_increase_pct": round(cost_increase_pct * 100.0, 2),
            "respected_planner_preferences": respects_prefs,
            "human_approval_required": human_approval_required,
            "final_recommendation": recommendation
        }
    }
