"""
Evaluation Agent.
Scores proposed mitigation alternatives on KPIs like cost, speed, risk, and service impact.
"""

from typing import List, Dict, Any, Optional
import config
from tools import evaluation_tools, data_tools

# Demonstrate Google ADK Pattern Imports:
try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

class EvaluationAgent:
    """Agent specialized in quantifying plan performance using business metrics."""
    
    def __init__(self):
        self.instruction = (
            "You are the Evaluation Analyst Agent. Your role is to compute key performance "
            "indicators (OTIF ratios, CO2 index, recovery expenditures) of routing changes, "
            "adhering to the metrics procedures mapped in skills/evaluation_skill.md."
        )
        
        # Google ADK Pattern: Bind tools and instructions to GenAI client
        self.agent = None
        self.client = None
        if HAS_GENAI and config.has_live_gemini_runtime():
            try:
                self.client = config.create_genai_client()
                if hasattr(types, "AgentConfig") and hasattr(self.client, "agents"):
                    self.agent = self.client.agents.create(
                        model=config.GEMINI_MODEL,
                        config=types.AgentConfig(
                            system_instruction=self.instruction,
                            tools=[evaluation_tools.evaluate_plan_kpis]
                        )
                    )
            except Exception as e:
                self.agent = None

    def score_plan(self, plan_actions: List[Dict[str, Any]], baseline_cost: float = 33260.22) -> Dict[str, Any]:
        """
        Evaluate and score list of plan actions.
        """
        if self.agent:
            try:
                # ADK run invocation
                response = self.agent.run(f"Evaluate performance scorecard: {plan_actions}")
            except Exception:
                pass
                
        # Deterministic fallback
        kpis = evaluation_tools.evaluate_plan_kpis(plan_actions)
        prefs = data_tools.load_planner_preferences()
        kpis = evaluation_tools.apply_preferences_to_evaluation(kpis, baseline_cost, prefs)
        return kpis
