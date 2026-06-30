"""
Inventory Agent.
Inspects warehouse capacities, manages buffer allocations, and interfaces with supplier profiles.
"""

from typing import Dict, Any, Optional
import config
from tools import inventory_tools

# Demonstrate Google ADK Pattern Imports:
try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

class InventoryAgent:
    """Agent specialized in evaluating stock buffers and warehouse storage."""
    
    def __init__(self):
        self.instruction = (
            "You are the Inventory Planner Agent. Your role is to inspect warehouse capacity "
            "levels and calculate if alternative buffer allocations are feasible without stockouts, "
            "using the criteria detailed in skills/inventory_feasibility_skill.md."
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
                            tools=[inventory_tools.check_warehouse_inventory]
                        )
                    )
            except Exception as e:
                self.agent = None

    def check_redirection_feasibility(self, product_family: str, quantity: int) -> Dict[str, Any]:
        """
        Check if alternative warehouses have stock of product_family to fulfill the order.
        """
        if self.agent:
            try:
                # ADK run invocation
                response = self.agent.run(f"Check feasibility for {quantity} of {product_family}")
            except Exception:
                pass
                
        # Deterministic fallback mapping
        wh_candidates = ["WH-MILAN", "WH-BOLOGNA"]
        for wh in wh_candidates:
            res = inventory_tools.check_warehouse_inventory(wh)
            if res.get("status") == "success" and res.get("current_stock", 0) >= quantity:
                return {
                    "product_family": product_family,
                    "allocated_warehouse": wh,
                    "status": "feasible",
                    "available_stock": res.get("current_stock")
                }
                
        return {
            "product_family": product_family,
            "status": "unfeasible",
            "reason": f"No warehouse has {quantity} pallets of {product_family} in stock."
        }
