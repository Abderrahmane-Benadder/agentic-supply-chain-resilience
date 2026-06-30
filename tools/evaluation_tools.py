"""
Evaluation utilities to score plans based on cost, speed, reliability, and security metrics.
"""

from typing import Dict, Any, List

def evaluate_plan_kpis(plan_actions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate simulated performance impact of a mitigation plan.
    
    Args:
        plan_actions: List of dictionary descriptions of action steps.
    """
    total_cost = 0.0
    delay_saved_hours = 0.0
    risk_score = 0.1  # base risk
    
    for action in plan_actions:
        cost = action.get("cost_usd", 0.0)
        total_cost += cost
        
        # Calculate impact metrics
        if "reroute" in action.get("type", "").lower():
            delay_saved_hours += action.get("hours_saved", 4.0)
        elif "expedite" in action.get("type", "").lower():
            delay_saved_hours += action.get("hours_saved", 8.0)
            risk_score += 0.05
        elif "substitute" in action.get("type", "").lower():
            delay_saved_hours += action.get("hours_saved", 12.0)
            risk_score += 0.15

    # Estimate CO2 emissions baseline + small penalty per action
    total_co2 = 16604.0
    for action in plan_actions:
        total_co2 += action.get("co2_kg", 54.0)

    # Resilience score calculation
    resilience_score = 100.0
    if total_cost > 0:
        savings_ratio = delay_saved_hours / (total_cost / 100.0)
        resilience_score = min(100.0, max(0.0, 50.0 + (savings_ratio * 10.0) - (risk_score * 20.0)))
    
    return {
        "total_recovery_cost_usd": round(total_cost, 2),
        "total_delay_hours_saved": round(delay_saved_hours, 1),
        "total_co2_emissions_kg": round(total_co2, 1),
        "post_plan_risk_score": round(risk_score, 2),
        "resilience_score": round(resilience_score, 1),
        "status": "feasible" if resilience_score > 40.0 else "high_risk_unfeasible"
    }

def calculate_service_level(plan: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate SLA On-Time In-Full (OTIF) rate based on shipping plan metrics.
    
    Args:
        plan: List of delivery route assignments.
    """
    total = len(plan)
    if total == 0:
        return {"otif_pct": 100.0, "total_orders": 0, "late_orders": 0}
        
    late_count = 0
    for item in plan:
        # Check if actual travel hours exceed expected due times
        # If travel time > due day in hours (due_day * 24), then it is late
        due_hours = float(item.get("due_day", 5)) * 24.0
        est_hours = float(item.get("hours_saved", 4.0)) # mapping fallback
        if est_hours > due_hours:
            late_count += 1
            
    otif = round(((total - late_count) / total) * 100.0, 2)
    return {
        "otif_pct": otif,
        "total_orders": total,
        "late_orders": late_count
    }

def calculate_total_cost(plan: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate sum cost of transport freight and associated delay SLA penalties.
    """
    freight = sum(float(item.get("cost_usd", 0.0)) for item in plan)
    
    # Delay penalties: say $500 for every order that saves less than 3 hours
    penalties = 0.0
    for item in plan:
        if float(item.get("hours_saved", 4.0)) < 3.0:
            penalties += 500.0
            
    return {
        "total_cost_usd": round(freight + penalties, 2),
        "freight_cost_usd": round(freight, 2),
        "penalty_cost_usd": round(penalties, 2)
    }

def calculate_total_co2(plan: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate total carbon footprint emitted across all transport routes.
    """
    # Assuming co2 per km average is 0.85 kg if not specified
    total_co2 = 0.0
    for item in plan:
        dist = float(item.get("distance_km", 200.0))
        co2_factor = float(item.get("co2_kg_per_km", 0.82))
        total_co2 += dist * co2_factor
        
    return {
        "total_co2_kg": round(total_co2, 2)
    }

def compare_baseline_disrupted_recovery(
    baseline: Dict[str, Any],
    disrupted: Dict[str, Any],
    recovery: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Assemble comparative metrics table between baseline, disrupted, and recovery states.
    """
    return {
        "comparison_table": {
            "metric": [
                "Freight Cost (USD)", 
                "Service Level (OTIF %)", 
                "CO2 Footprint (kg)", 
                "Total Delay (hrs)"
            ],
            "baseline": [
                baseline.get("cost_usd", 12000.0), 
                baseline.get("otif_pct", 100.0), 
                baseline.get("co2_kg", 5400.0), 
                baseline.get("delay_hours", 0.0)
            ],
            "disrupted": [
                disrupted.get("cost_usd", 12000.0), 
                disrupted.get("otif_pct", 65.0), 
                disrupted.get("co2_kg", 5400.0), 
                disrupted.get("delay_hours", 72.0)
            ],
            "recovery": [
                recovery.get("cost_usd", 14500.0), 
                recovery.get("otif_pct", 95.0), 
                recovery.get("co2_kg", 6100.0), 
                recovery.get("delay_hours", 12.0)
            ]
        },
        "cost_variance_usd": round(recovery.get("cost_usd", 14500.0) - baseline.get("cost_usd", 12000.0), 2),
        "service_level_recovery_pct": round(recovery.get("otif_pct", 95.0) - disrupted.get("otif_pct", 65.0), 2)
    }

def apply_preferences_to_evaluation(evaluation_result: Dict[str, Any], baseline_cost: float, prefs: Dict[str, Any]) -> Dict[str, Any]:
    """Applies planner preferences to adjust recovery status and verification gates."""
    rec_cost = evaluation_result.get("total_recovery_cost_usd", evaluation_result.get("total_cost_usd", 0.0))
    cost_increase_pct = 0.0
    if baseline_cost > 0:
        cost_increase_pct = (rec_cost - baseline_cost) / baseline_cost
        
    human_approval = cost_increase_pct > prefs.get("human_approval_required_if_cost_increase_above", 0.15)
    otif = (evaluation_result.get("otif_pct", 100.0) or 100.0) / 100.0 # scale to 0-1
    service_target = prefs.get("service_level_target", 0.95)
    
    target_met = otif >= service_target
    
    evaluation_result["human_approval_required"] = human_approval
    evaluation_result["meets_service_target"] = target_met
    evaluation_result["cost_increase_pct"] = round(cost_increase_pct * 100.0, 2)
    
    if human_approval or not target_met:
        evaluation_result["status"] = "pending_human_review"
    else:
        evaluation_result["status"] = "auto_approved"
        
    return evaluation_result

