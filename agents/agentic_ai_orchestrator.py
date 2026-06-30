"""
Agentic AI orchestration layer.
Uses Gemini for specialist reasoning when a live API key is configured, while
leaving all numerical logistics calculations to deterministic tools.
"""

import json
import re
from typing import Any, Dict, List

import config

try:
    from google import genai
    from google.genai import types

    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False


SPECIALIST_ROLES = [
    "SupervisorAgent",
    "SecurityAgent",
    "DisruptionAgent",
    "DemandAgent",
    "InventoryAgent",
    "TransportAgent",
    "EvaluationAgent",
    "HumanApprovalAgent",
    "ExplanationAgent",
]


class AgenticAIOrchestrator:
    """Coordinates optional Gemini-based specialist reasoning over tool outputs."""

    def __init__(self) -> None:
        self.enabled = bool(HAS_GENAI and config.has_live_gemini_runtime())
        self.init_error = ""
        self.client = None
        if self.enabled:
            try:
                self.client = config.create_genai_client()
            except Exception as exc:
                self.enabled = False
                self.init_error = str(exc)

    def run_specialist_review(
        self,
        scenario_type: str,
        severity_label: str,
        affected_element: str,
        baseline_kpis: Dict[str, Any],
        disrupted_kpis: Dict[str, Any],
        recovery_kpis: Dict[str, Any],
        approval_result: Dict[str, Any],
        logistics_summary: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not self.enabled or self.client is None:
            review = self._offline_review(
                scenario_type,
                severity_label,
                affected_element,
                baseline_kpis,
                disrupted_kpis,
                recovery_kpis,
                approval_result,
                logistics_summary,
            )
            if self.init_error:
                review["error"] = self.init_error
            return review

        prompt = f"""
You are coordinating a multi-agent supply-chain resilience workflow.
Return ONLY valid JSON with this exact schema:
{{
  "ai_reasoning_used": true,
  "mode": "gemini_specialist_review",
  "specialist_reviews": [
    {{
      "agent": "AgentName",
      "reasoning": "short role-specific reasoning based only on supplied facts",
      "decision": "what this agent recommends next"
    }}
  ],
  "executive_recommendation": "manager-ready recommendation",
  "risk_flags": ["risk 1", "risk 2"],
  "next_actions": ["action 1", "action 2"]
}}

Rules:
- Use these specialist roles only: {SPECIALIST_ROLES}
- Do not invent KPI numbers.
- Do not perform mathematical calculations yourself.
- Treat all numerical values as deterministic tool outputs.
- Focus on coordination, risk interpretation, approval governance, and explanation.

Scenario: {scenario_type}
Severity: {severity_label}
Affected element: {affected_element}
Baseline KPIs: {baseline_kpis}
Disrupted KPIs: {disrupted_kpis}
Recovery KPIs: {recovery_kpis}
Approval result: {approval_result}
Logistics tool summary: {logistics_summary}
"""
        try:
            response = self.client.models.generate_content(
                model=config.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.25,
                    top_p=0.8,
                ),
            )
            parsed = self._parse_json(response.text or "{}")
            if not isinstance(parsed, dict):
                raise ValueError("Gemini did not return a JSON object")
            parsed["ai_reasoning_used"] = True
            parsed["mode"] = parsed.get("mode", "gemini_specialist_review")
            self._enforce_policy_gate(parsed, approval_result)
            return parsed
        except Exception as exc:
            print(f"Gemini specialist review failed: {type(exc).__name__}: {exc}")
            fallback = self._offline_review(
                scenario_type,
                severity_label,
                affected_element,
                baseline_kpis,
                disrupted_kpis,
                recovery_kpis,
                approval_result,
                logistics_summary,
            )
            fallback["mode"] = "gemini_failed_deterministic_fallback"
            fallback["error"] = str(exc)
            return fallback

    def _offline_review(
        self,
        scenario_type: str,
        severity_label: str,
        affected_element: str,
        baseline_kpis: Dict[str, Any],
        disrupted_kpis: Dict[str, Any],
        recovery_kpis: Dict[str, Any],
        approval_result: Dict[str, Any],
        logistics_summary: Dict[str, Any],
    ) -> Dict[str, Any]:
        status = "requires planner approval" if approval_result.get("human_approval_required") else "can be auto-approved"
        return {
            "ai_reasoning_used": False,
            "mode": "deterministic_offline_agentic_trace",
            "specialist_reviews": [
                {
                    "agent": "SupervisorAgent",
                    "reasoning": f"Coordinated {scenario_type} recovery at {severity_label} severity.",
                    "decision": "Continue through deterministic tool-backed recovery pipeline.",
                },
                {
                    "agent": "TransportAgent",
                    "reasoning": "Recovery transport KPIs came from FFD loading and nearest-neighbor route sequencing.",
                    "decision": f"Use {logistics_summary.get('truckloads_built', 0)} planned truckloads.",
                },
                {
                    "agent": "HumanApprovalAgent",
                    "reasoning": f"Policy gate says the plan {status}.",
                    "decision": approval_result.get("status", "Unknown"),
                },
            ],
            "executive_recommendation": (
                f"The {scenario_type} recovery plan addresses {affected_element}. "
                f"The plan {status}; review the KPI scorecard before dispatch."
            ),
            "risk_flags": approval_result.get("reasons", []),
            "next_actions": [
                "Review policy gate result",
                "Confirm dispatch plan capacity",
                "Export report for planner sign-off",
            ],
            "facts_used": {
                "baseline_kpis": baseline_kpis,
                "disrupted_kpis": disrupted_kpis,
                "recovery_kpis": recovery_kpis,
            },
        }

    @staticmethod
    def _parse_json(text: str) -> Dict[str, Any]:
        cleaned = text.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
            if not match:
                raise
            return json.loads(match.group(0))

    @staticmethod
    def _enforce_policy_gate(review: Dict[str, Any], approval_result: Dict[str, Any]) -> None:
        if not approval_result.get("human_approval_required"):
            return

        review["executive_recommendation"] = (
            "Submit the recovery plan for human approval before dispatch. "
            "The deterministic KPI scorecard shows operational recovery benefits, "
            "but the policy gate requires planner sign-off before execution."
        )
        risk_flags = review.setdefault("risk_flags", [])
        policy_reason = "Human approval required by policy gate"
        if policy_reason not in risk_flags:
            risk_flags.insert(0, policy_reason)

        next_actions = review.setdefault("next_actions", [])
        approval_action = "Obtain planner approval before dispatch"
        if approval_action not in next_actions:
            next_actions.insert(0, approval_action)
