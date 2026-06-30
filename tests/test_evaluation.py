"""
Unit tests for mathematical metric equations, service levels, co2 indexes, and comparisons.
"""

from evaluation import metrics
from tools import evaluation_tools

def test_calculate_otif():
    """Verify OTIF calculation arithmetic."""
    assert metrics.calculate_otif(total_orders=100, late_orders=5, incomplete_orders=2) == 93.00
    assert metrics.calculate_otif(total_orders=0, late_orders=0, incomplete_orders=0) == 100.00

def test_calculate_resilience_index():
    """Verify resilience score metrics."""
    score = metrics.calculate_resilience_index(recovery_cost=1000.0, delay_hours_saved=10.0, base_sla_penalty=2000.0)
    assert score == 15.0

def test_evaluate_plan_kpis():
    """Verify tools formula score yields expected metrics dictionary."""
    actions = [
        {"type": "reroute", "cost_usd": 1500.0, "hours_saved": 8.0},
        {"type": "expedite", "cost_usd": 2500.0, "hours_saved": 12.0}
    ]
    kpis = evaluation_tools.evaluate_plan_kpis(actions)
    assert kpis["total_recovery_cost_usd"] == 4000.0
    assert kpis["total_delay_hours_saved"] == 20.0

def test_calculate_service_level():
    """Verify OTIF service level calculations from shipping plan metrics."""
    plan = [
        {"order_id": "ORD-1", "due_day": 3, "hours_saved": 8.0},
        {"order_id": "ORD-2", "due_day": 1, "hours_saved": 48.0} # late (48 > 24)
    ]
    res = evaluation_tools.calculate_service_level(plan)
    assert res["otif_pct"] == 50.0
    assert res["total_orders"] == 2
    assert res["late_orders"] == 1

def test_calculate_total_cost():
    """Verify cost calculations including delay penalties."""
    plan = [
        {"order_id": "ORD-1", "cost_usd": 1200.0, "hours_saved": 5.0}, # no penalty
        {"order_id": "ORD-2", "cost_usd": 800.0, "hours_saved": 2.0}   # penalty of $500
    ]
    res = evaluation_tools.calculate_total_cost(plan)
    assert res["total_cost_usd"] == 2500.0
    assert res["freight_cost_usd"] == 2000.0
    assert res["penalty_cost_usd"] == 500.0

def test_calculate_total_co2():
    """Verify carbon index emissions totals."""
    plan = [
        {"order_id": "ORD-1", "distance_km": 200.0, "co2_kg_per_km": 0.82},
        {"order_id": "ORD-2", "distance_km": 300.0, "co2_kg_per_km": 0.82}
    ]
    res = evaluation_tools.calculate_total_co2(plan)
    # total distance = 500km * 0.82 = 410.0 kg
    assert res["total_co2_kg"] == 410.0

def test_compare_baseline_disrupted_recovery():
    """Verify scorecard compilation logic."""
    baseline = {"cost_usd": 10000.0, "otif_pct": 100.0, "co2_kg": 4000.0, "delay_hours": 0.0}
    disrupted = {"cost_usd": 10000.0, "otif_pct": 50.0, "co2_kg": 4000.0, "delay_hours": 96.0}
    recovery = {"cost_usd": 12000.0, "otif_pct": 90.0, "co2_kg": 4800.0, "delay_hours": 12.0}
    
    res = evaluation_tools.compare_baseline_disrupted_recovery(baseline, disrupted, recovery)
    assert "comparison_table" in res
    assert res["cost_variance_usd"] == 2000.0
    assert res["service_level_recovery_pct"] == 40.0
