"""
Lightweight reinforcement-learning policy agent.

This is a contextual bandit, not a deep RL route optimizer. It learns which
business recovery posture performs best for each scenario/severity context from
observed KPI rewards across repeated simulations.
"""

import json
from pathlib import Path
from typing import Any, Dict

import config


POLICY_ACTIONS = ["balanced", "service_first", "cost_guarded", "co2_aware"]


class ReinforcementLearningAgent:
    """Learns scenario-level recovery policy preferences from KPI outcomes."""

    def __init__(self, policy_path: Path | None = None) -> None:
        self.policy_path = policy_path or (config.MEMORIES_DIR / "rl_policy.json")
        self.policy = self._load_policy()

    def choose_action(self, scenario_type: str, severity_label: str, planner_preferences: Dict[str, Any]) -> Dict[str, Any]:
        state_key = self._state_key(scenario_type, severity_label)
        q_values = self.policy.setdefault(state_key, {action: 0.0 for action in POLICY_ACTIONS})

        preferred_action = self._preference_prior(planner_preferences)
        if all(value == 0.0 for value in q_values.values()):
            action = preferred_action
        else:
            action = max(q_values, key=q_values.get)

        return {
            "state": state_key,
            "action": action,
            "q_values": {key: round(value, 4) for key, value in q_values.items()},
            "preference_prior": preferred_action,
        }

    def update_from_outcome(
        self,
        state_key: str,
        action: str,
        baseline_kpis: Dict[str, Any],
        disrupted_kpis: Dict[str, Any],
        recovery_kpis: Dict[str, Any],
        approval_result: Dict[str, Any],
        alpha: float = 0.25,
    ) -> Dict[str, Any]:
        q_values = self.policy.setdefault(state_key, {policy_action: 0.0 for policy_action in POLICY_ACTIONS})
        if action not in q_values:
            action = "balanced"

        reward = self._calculate_reward(baseline_kpis, disrupted_kpis, recovery_kpis, approval_result)
        old_value = q_values[action]
        new_value = old_value + alpha * (reward - old_value)
        q_values[action] = new_value
        self._save_policy()

        return {
            "state": state_key,
            "action": action,
            "reward": round(reward, 4),
            "old_q": round(old_value, 4),
            "new_q": round(new_value, 4),
            "q_values": {key: round(value, 4) for key, value in q_values.items()},
        }

    def _calculate_reward(
        self,
        baseline_kpis: Dict[str, Any],
        disrupted_kpis: Dict[str, Any],
        recovery_kpis: Dict[str, Any],
        approval_result: Dict[str, Any],
    ) -> float:
        base_cost = float(baseline_kpis.get("cost_usd", 0.0) or 0.0)
        disrupted_otif = float(disrupted_kpis.get("otif_pct", 0.0) or 0.0)
        recovery_otif = float(recovery_kpis.get("otif_pct", 0.0) or 0.0)
        recovery_cost = float(recovery_kpis.get("cost_usd", 0.0) or 0.0)
        recovery_delay = float(recovery_kpis.get("delay_hours", 0.0) or 0.0)
        recovery_co2 = float(recovery_kpis.get("co2_kg", 0.0) or 0.0)
        baseline_co2 = float(baseline_kpis.get("co2_kg", recovery_co2) or recovery_co2)

        service_gain = max(0.0, recovery_otif - disrupted_otif) / 100.0
        cost_penalty = ((recovery_cost - base_cost) / base_cost) if base_cost else 0.0
        delay_penalty = min(recovery_delay / 72.0, 1.0)
        co2_penalty = max(0.0, (recovery_co2 - baseline_co2) / baseline_co2) if baseline_co2 else 0.0
        approval_penalty = 0.1 if approval_result.get("human_approval_required") else 0.0

        reward = (1.4 * service_gain) - (0.7 * cost_penalty) - (0.2 * delay_penalty) - (0.2 * co2_penalty) - approval_penalty
        return max(-1.0, min(1.0, reward))

    def _load_policy(self) -> Dict[str, Dict[str, float]]:
        if not self.policy_path.exists():
            return {}
        try:
            with open(self.policy_path, "r", encoding="utf-8") as policy_file:
                data = json.load(policy_file)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _save_policy(self) -> None:
        self.policy_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.policy_path, "w", encoding="utf-8") as policy_file:
            json.dump(self.policy, policy_file, indent=2)

    @staticmethod
    def _state_key(scenario_type: str, severity_label: str) -> str:
        return f"{scenario_type}:{severity_label}"

    @staticmethod
    def _preference_prior(planner_preferences: Dict[str, Any]) -> str:
        if planner_preferences.get("co2_priority") == "high":
            return "co2_aware"
        if planner_preferences.get("cost_priority") == "high":
            return "cost_guarded"
        service_target = float(planner_preferences.get("service_level_target", 0.95))
        if service_target >= 0.95:
            return "service_first"
        return "balanced"
