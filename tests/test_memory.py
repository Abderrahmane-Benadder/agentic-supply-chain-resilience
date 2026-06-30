"""
Unit tests for persistent memory preferences and session state trackers.
"""

import os
from tools import data_tools, evaluation_tools

def test_preferences_persistence():
    # Load default preferences
    prefs = data_tools.load_planner_preferences()
    assert "min_truck_utilization" in prefs
    assert "service_level_target" in prefs
    
    # Modify preferences temporarily
    original_target = prefs["service_level_target"]
    prefs["service_level_target"] = 0.99
    
    res = data_tools.update_planner_preferences(prefs)
    assert res is True
    
    new_prefs = data_tools.load_planner_preferences()
    assert new_prefs["service_level_target"] == 0.99
    
    # Restore original preferences
    new_prefs["service_level_target"] = original_target
    data_tools.update_planner_preferences(new_prefs)

def test_session_state_persistence():
    state = data_tools.load_session_state()
    assert isinstance(state, dict)
    
    test_state = {
        "selected_scenario": "Test Scenario",
        "severity": "high",
        "baseline_kpis": {"cost_usd": 100},
        "disrupted_kpis": {"cost_usd": 200},
        "recovery_kpis": {"cost_usd": 150},
        "agent_trace": [{"step": "test", "status": "done"}],
        "final_decision": "Approved"
    }
    
    res = data_tools.save_session_state(test_state)
    assert res is True
    
    loaded = data_tools.load_session_state()
    assert loaded["selected_scenario"] == "Test Scenario"
    assert loaded["severity"] == "high"
    assert loaded["final_decision"] == "Approved"

def test_apply_preferences_to_evaluation():
    prefs = {
        "service_level_target": 0.95,
        "human_approval_required_if_cost_increase_above": 0.10
    }
    
    # Case 1: Meets OTIF and costs are low -> auto approved
    kpis = {"otif_pct": 98.0, "total_recovery_cost_usd": 1000.0}
    res = evaluation_tools.apply_preferences_to_evaluation(kpis, 950.0, prefs)
    assert res["status"] == "auto_approved"
    assert res["meets_service_target"] is True
    assert res["human_approval_required"] is False
    
    # Case 2: OTIF falls below target -> pending review
    kpis2 = {"otif_pct": 90.0, "total_recovery_cost_usd": 1000.0}
    res2 = evaluation_tools.apply_preferences_to_evaluation(kpis2, 950.0, prefs)
    assert res2["status"] == "pending_human_review"
    assert res2["meets_service_target"] is False
    
    # Case 3: Cost increase too high -> pending review
    kpis3 = {"otif_pct": 98.0, "total_recovery_cost_usd": 1200.0}
    res3 = evaluation_tools.apply_preferences_to_evaluation(kpis3, 950.0, prefs)
    assert res3["status"] == "pending_human_review"
    assert res3["human_approval_required"] is True
