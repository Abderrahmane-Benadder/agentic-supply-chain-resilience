"""
Demand Agent.
Analyzes orders, customer priorities, and estimates backlog and SLA delay risks.
"""

from typing import List, Dict, Any, Optional
import config
from tools import data_tools

# Demonstrate Google ADK Pattern Imports:
try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

class DemandAgent:
    """Agent specialized in evaluating customer order priority and demand trends."""
    
    def __init__(self):
        self.instruction = (
            "You are the Demand Analyst Agent. Your role is to examine active customer orders "
            "impacted by transportation closures and categorize them by SLA due date urgency, "
            "adhering to the procedural parameters defined in skills/demand_analysis_skill.md."
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
                            tools=[data_tools.load_orders]
                        )
                    )
            except Exception as e:
                self.agent = None

    def analyze_affected_demand(self, location: str) -> List[Dict[str, Any]]:
        """
        Load active orders and filter for those affected by a disruption at `location`.
        """
        if self.agent:
            try:
                # ADK run invocation
                response = self.agent.run(f"Identify orders destined for {location}")
            except Exception:
                pass
                
        # Deterministic fallback
        try:
            orders_df = data_tools.load_dataset("orders")
            affected = orders_df[
                orders_df["customer_city"].str.lower() == location.lower()
            ]
            return affected.to_dict(orient="records")
        except Exception:
            return []
