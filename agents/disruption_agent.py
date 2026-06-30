"""
Disruption Agent.
Analyzes weather feeds, labor strikes, and port outages to evaluate supply chain impacts.
"""

from typing import List, Dict, Any, Optional
import config
from tools import disruption_tools

# Demonstrate Google ADK Pattern Imports:
try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

class DisruptionAgent:
    """Agent specialized in identifying and evaluating network disruptions."""
    
    def __init__(self):
        self.instruction = (
            "You are the Disruption Analyst Agent. Your role is to identify and classify "
            "active logistics hazards (e.g. weather alerts, strikes, closures) affecting cities in Italy."
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
                            tools=[disruption_tools.check_active_disruptions]
                        )
                    )
            except Exception as e:
                self.agent = None

    def analyze_impact(self, location: str) -> List[Dict[str, Any]]:
        """
        Check and filter disruptions occurring at the given location.
        """
        if self.agent:
            try:
                # ADK active invocation
                response = self.agent.run(f"Identify disruptions in {location}")
                # A full implementation would parse and return structured items
            except Exception:
                pass
                
        # Deterministic fallback
        return disruption_tools.check_active_disruptions(location)
