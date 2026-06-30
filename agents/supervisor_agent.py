"""
Supervisor Agent (Orchestrator).
Coordinates disruption handling by routing requests to specialized agents
and synthesizing the final mitigation plan.
"""

import uuid
from typing import Dict, Any, List
import config
from mcp_server.tool_registry import registry
from agents.disruption_agent import DisruptionAgent
from agents.demand_agent import DemandAgent
from agents.inventory_agent import InventoryAgent
from agents.transport_agent import TransportAgent
from agents.evaluation_agent import EvaluationAgent
from agents.security_agent import SecurityAgent
from agents.explanation_agent import ExplanationAgent
from tools import report_tools

# Demonstrate Google ADK Pattern Imports:
try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

class SupervisorAgent:
    """Orchestrator agent coordinating the supply chain mitigation workflow."""
    
    def __init__(self):
        self.disruption_agent = DisruptionAgent()
        self.demand_agent = DemandAgent()
        self.inventory_agent = InventoryAgent()
        self.transport_agent = TransportAgent()
        self.evaluation_agent = EvaluationAgent()
        self.security_agent = SecurityAgent()
        self.explanation_agent = ExplanationAgent()

        self.instruction = (
            "You are the Orchestrator Supervisor Agent. Your role is to delegate "
            "sub-components of crises mitigation to specialists (Disruption, Demand, "
            "Inventory, and Transport Agents), validate constraints via SecurityProxy, "
            "calculate KPIs via EvaluationAgent, and present narrative justifications."
        )

        # Google ADK Pattern: Bind orchestration flow
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

    def run_mitigation_workflow(self, scenario_name: str, location: str) -> Dict[str, Any]:
        """
        Coordinates the multi-agent resilience workflow.
        
        Args:
            scenario_name: Description of the crisis (e.g. Typhoon Alert).
            location: Affected geographic node.
        """
        session_id = str(uuid.uuid4())[:8]
        trace_steps = []
        
        # 1. Security Check on input
        trace_steps.append({"step": "Security Check", "status": "Initiated"})
        if not self.security_agent.validate_input(scenario_name + " " + location):
            return {
                "session_id": session_id,
                "status": "Rejected",
                "reason": "Input failed security policy / safety guardrails."
            }
        trace_steps.append({"step": "Security Check", "status": "Passed"})

        # 2. Analyze Disruption
        trace_steps.append({"step": "Disruption Analysis", "status": "Delegated"})
        disruptions = self.disruption_agent.analyze_impact(location)
        trace_steps.append({
            "step": "Disruption Analysis",
            "status": "Completed",
            "output": disruptions
        })

        # 3. Determine Affected Demand
        trace_steps.append({"step": "Demand Impact Analysis", "status": "Delegated"})
        orders = self.demand_agent.analyze_affected_demand(location)
        trace_steps.append({
            "step": "Demand Impact Analysis",
            "status": "Completed",
            "output": orders
        })

        # 4. Evaluate Inventory buffer levels & alternatives
        trace_steps.append({"step": "Inventory Feasibility check", "status": "Delegated"})
        inventory_options = []
        for o in orders:
            wh_check = self.inventory_agent.check_redirection_feasibility(o["product_family"], o["pallets"])
            inventory_options.append(wh_check)
        trace_steps.append({
            "step": "Inventory Feasibility check",
            "status": "Completed",
            "output": inventory_options
        })

        # 5. Formulate alternative Transport routing
        trace_steps.append({"step": "Transport Re-routing", "status": "Delegated"})
        transport_routes = []
        for o in orders:
            routes = self.transport_agent.find_alternative_routes(location, o["customer_city"], 5.0)
            transport_routes.append(routes)
        trace_steps.append({
            "step": "Transport Re-routing",
            "status": "Completed",
            "output": transport_routes
        })

        # 6. Synthesize plan and evaluate it
        trace_steps.append({"step": "Plan Formulation", "status": "Synthesizing"})
        # Simple heuristic synthesis combining inventory shifts & routes
        plan_actions = []
        for idx, o in enumerate(orders):
            plan_actions.append({
                "type": "reroute_order",
                "order_id": o["order_id"],
                "source": location,
                "destination": o["customer_city"],
                "cost_usd": transport_routes[idx].get("cost_usd", 1200.0) if idx < len(transport_routes) else 1200.0,
                "hours_saved": 6.0
            })
            
        evaluation_result = self.evaluation_agent.score_plan(plan_actions)
        trace_steps.append({
            "step": "Plan Evaluation",
            "status": "Completed",
            "output": evaluation_result
        })

        # 7. Post-execution Security Validation
        trace_steps.append({"step": "Plan Verification", "status": "Auditing"})
        plan_validated = self.security_agent.validate_output(plan_actions, evaluation_result)
        if not plan_validated:
            return {
                "session_id": session_id,
                "status": "Blocked",
                "reason": "Synthesized plan violated safety constraints (e.g. budget exceedance)."
            }
        trace_steps.append({"step": "Plan Verification", "status": "Verified"})

        # 8. Human explanation translation
        trace_steps.append({"step": "Explanation Generation", "status": "Delegated"})
        explanation = self.explanation_agent.generate_explanation(disruptions, plan_actions, evaluation_result)
        trace_steps.append({
            "step": "Explanation Generation",
            "status": "Completed",
            "output": explanation
        })

        # Compile final outputs
        final_summary = {
            "session_id": session_id,
            "scenario": scenario_name,
            "location": location,
            "disruptions": disruptions,
            "orders_impacted": orders,
            "plan_actions": plan_actions,
            "evaluation": evaluation_result,
            "explanation": explanation,
            "status": "Mitigation Plan Active"
        }
        
        # Save trace & report
        report_tools.save_agent_trace(session_id, {"steps": trace_steps, "final_summary": final_summary})
        report_path = report_tools.generate_mitigation_markdown_report(
            session_id, scenario_name, disruptions, evaluation_result, explanation
        )
        
        final_summary["report_path"] = report_path

        # Persistent Memory and Session State update
        from tools import data_tools
        session_data = {
            "selected_scenario": scenario_name,
            "severity": "medium",
            "baseline_kpis": {
                "cost_usd": 33260.22,
                "otif_pct": 100.0,
                "co2_kg": 16604.0,
                "delay_hours": 0.0
            },
            "disrupted_kpis": {
                "cost_usd": evaluation_result.get("total_recovery_cost_usd", 1400.0) * 1.25,
                "otif_pct": 75.0,
                "co2_kg": 16604.0,
                "delay_hours": 36.0
            },
            "recovery_kpis": {
                "cost_usd": evaluation_result.get("total_recovery_cost_usd", 1400.0),
                "otif_pct": evaluation_result.get("otif_pct", 95.0),
                "co2_kg": 16604.0,
                "delay_hours": evaluation_result.get("total_delay_hours_saved", 6.0)
            },
            "agent_trace": trace_steps,
            "final_decision": "Approved" if evaluation_result.get("status") == "auto_approved" else "Pending Human Approval"
        }
        data_tools.save_session_state(session_data)

        return final_summary
