"""
Transport Agent.
Identifies shipping options, verifies vehicle status, and computes optimal route shifts.
"""

from typing import Dict, Any, List, Optional
import config
from tools import transport_tools

# Demonstrate Google ADK Pattern Imports:
try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

class TransportAgent:
    """Agent specialized in dispatching freight carriers and route planning."""
    
    def __init__(self):
        self.instruction = (
            "You are the Transportation Planner Agent. Your role is to examine route distances, "
            "calculate transit durations, and select the optimal carriage assignment, "
            "adhering to the procedures in skills/transport_recovery_skill.md."
        )
        
        # Google ADK Pattern: Bind tools and instructions to GenAI client
        self.agent = None
        self.client = None
        if HAS_GENAI and config.has_valid_gemini_key():
            try:
                self.client = genai.Client(api_key=config.GEMINI_API_KEY)
                if hasattr(types, "AgentConfig") and hasattr(self.client, "agents"):
                    self.agent = self.client.agents.create(
                        model=config.GEMINI_MODEL,
                        config=types.AgentConfig(
                            system_instruction=self.instruction,
                            tools=[
                                transport_tools.find_available_trucks,
                                transport_tools.calculate_route_cost_and_time
                            ]
                        )
                    )
            except Exception as e:
                self.agent = None

    def find_alternative_routes(self, source: str, destination: str, tonnage: float) -> Dict[str, Any]:
        """
        Check for available trucks and compute routes.
        """
        if self.agent:
            try:
                # ADK run invocation
                response = self.agent.run(f"Find routes from {source} to {destination} for {tonnage} tons")
            except Exception:
                pass
                
        # Deterministic fallback
        available_trucks = transport_tools.find_available_trucks(source)
        route_estimate = transport_tools.calculate_route_cost_and_time(source, destination, tonnage)
        
        if route_estimate.get("status") == "success":
            return {
                "source": source,
                "destination": destination,
                "cost_usd": route_estimate.get("cost_usd"),
                "hours": route_estimate.get("estimated_hours"),
                "trucks_available_count": len(available_trucks),
                "allocated_truck": available_trucks[0]["truck_id"] if available_trucks else "TRK-EXTERNAL"
            }
            
        return {
            "status": "error",
            "reason": "Failed to calculate route metrics."
        }
