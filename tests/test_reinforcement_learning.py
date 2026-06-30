"""
Tests for the lightweight reinforcement-learning policy agent.
"""

from agents.reinforcement_learning_agent import ReinforcementLearningAgent


def test_rl_policy_updates_q_value(tmp_path):
    agent = ReinforcementLearningAgent(policy_path=tmp_path / "rl_policy.json")
    prefs = {
        "cost_priority": "high",
        "co2_priority": "medium",
        "service_level_target": 0.95,
    }

    choice = agent.choose_action("route_closure", "high", prefs)
    assert choice["action"] == "cost_guarded"

    update = agent.update_from_outcome(
        choice["state"],
        choice["action"],
        {"cost_usd": 1000.0, "otif_pct": 100.0, "co2_kg": 500.0},
        {"cost_usd": 1400.0, "otif_pct": 60.0, "co2_kg": 500.0},
        {"cost_usd": 1100.0, "otif_pct": 92.0, "co2_kg": 520.0, "delay_hours": 8.0},
        {"human_approval_required": False},
    )

    assert update["state"] == "route_closure:high"
    assert update["action"] == "cost_guarded"
    assert update["new_q"] != update["old_q"]
    assert (tmp_path / "rl_policy.json").exists()
