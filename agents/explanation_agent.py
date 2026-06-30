"""
Explanation Agent.
Translates structured agent data and trace sequences into clean, user-friendly rationales.
"""

from typing import List, Dict, Any, Optional
import config

# Demonstrate Google ADK Pattern Imports:
try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

class ExplanationAgent:
    """Agent specialized in interpreting plans and generating human explanations."""
    
    def __init__(self):
        self.instruction = (
            "You are the Explanation Agent. Your role is to translate complex routing tables "
            "and cost indices into plain, manager-friendly logistics briefs justifying mitigation decisions."
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
                            system_instruction=self.instruction
                        )
                    )
            except Exception as e:
                self.agent = None

    def generate_explanation(
        self,
        disruptions: List[Dict[str, Any]],
        plan_actions: List[Dict[str, Any]],
        evaluation_result: Dict[str, Any]
    ) -> str:
        """
        Produce a descriptive executive rationale explaining the plan decisions.
        """
        if not plan_actions:
            return "No recovery plan could be formulated because no active orders were impacted."
            
        disruption_summary = ", ".join([f"{d.get('type', 'Unknown')} at {d.get('location', 'Network')}" for d in disruptions])
        order_count = len(plan_actions)
        total_cost = evaluation_result.get("total_recovery_cost_usd", evaluation_result.get("total_cost_usd", 0.0))
        resilience = evaluation_result.get("resilience_score", 0.0)

        # ADK invocation
        if self.agent:
            try:
                prompt = (
                    f"Explain why we choose this plan for {order_count} orders affected by {disruption_summary}. "
                    f"Plan details: {plan_actions}. KPIs: {evaluation_result}."
                )
                response = self.agent.run(prompt)
                return response.text
            except Exception:
                pass
        
        # Deterministic rule-based fallback
        rationale = (
            f"Due to the active disruption ({disruption_summary}), we observed immediate threats "
            f"to {order_count} delivery orders. To prevent costly downtime and SLA penalties, "
            f"we initiated alternate carrier assignment and redirected warehouse stocks. "
            f"This plan is selected because it preserves critical timelines (saving approx "
            f"{evaluation_result.get('total_delay_hours_saved', 6.0)} hours) while maintaining "
            f"a resilience efficiency index of {resilience}/100. Total budget allocation "
            f"for this action is ${total_cost:,.2f}."
        )
        
        return rationale
