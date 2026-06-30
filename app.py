"""
Streamlit dashboard for the Agentic Supply Chain Resilience Platform.
"""

import json
import os
import re
from html import escape
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import config
from main import run_simulation
from tools import data_tools, inventory_tools, transport_tools

try:
    from google import genai
    from google.genai import types

    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False


SCENARIOS = {
    "demand_spike": {
        "label": "Demand spike",
        "title": "Italian market demand expansion",
        "detail": "Expanded customer demand is stressing pallet volume, warehouse stock, and outbound capacity.",
    },
    "truck_breakdown": {
        "label": "Truck breakdown",
        "title": "Primary fleet vehicle failure",
        "detail": "A scheduled vehicle is unavailable and active loads need fleet or carrier reallocation.",
    },
    "warehouse_bottleneck": {
        "label": "Warehouse bottleneck",
        "title": "Milan logistics hub throughput outage",
        "detail": "Reduced Milan throughput requires fallback inventory and alternative dispatch decisions.",
    },
    "route_closure": {
        "label": "Route closure",
        "title": "Milan to Rome corridor closure",
        "detail": "A blocked primary corridor forces route re-sequencing and higher recovery scrutiny.",
    },
    "custom_generative_prompt": {
        "label": "Custom generated case",
        "title": "Custom disruption case",
        "detail": "Gemini converts the planner description into a structured scenario, then maps it to a supported engine trigger.",
    },
}

TRACE_EXPLANATIONS = {
    "Security Check": "Validates prompt safety and tool permissions before the workflow continues.",
    "Disruption Analysis": "Identifies the affected lane, warehouse, fleet asset, or demand segment.",
    "Demand Impact Analysis": "Ranks exposed orders by service risk, due date, and operational priority.",
    "Inventory Feasibility check": "Checks available stock and warehouse alternatives.",
    "Transport Re-routing": "Uses FFD loading and nearest-neighbor sequencing to build a recovery movement plan.",
    "Plan Evaluation": "Compares baseline, disrupted, and recovery KPIs.",
    "Plan Verification": "Applies policy thresholds and human approval gates.",
    "Human Approval Gate": "Checks whether recovery cost or service performance requires planner sign-off.",
    "Agentic AI Specialist Review": "Runs Gemini specialist review when configured, or records deterministic fallback reasoning.",
    "RL Policy Update": "Updates lightweight contextual-bandit recovery policy values from KPI reward.",
    "Explanation Generation": "Produces the manager-facing recommendation and report output.",
}


def has_live_gemini() -> bool:
    return bool(HAS_GENAI and config.has_valid_gemini_key())


def extract_json_object(text: str) -> Dict[str, Any]:
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


def generate_json_with_gemini(prompt: str, fallback: Dict[str, Any]) -> Dict[str, Any]:
    if not has_live_gemini():
        return fallback

    try:
        client = genai.Client(api_key=config.GEMINI_API_KEY)
        response = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
                top_p=0.8,
            ),
        )
        parsed = extract_json_object(response.text or "{}")
        return parsed if isinstance(parsed, dict) else fallback
    except Exception as exc:
        st.sidebar.warning(f"Gemini returned fallback output: {exc}")
        return fallback


def money(value: float) -> str:
    return f"${float(value):,.0f}"


def pct(value: float) -> str:
    return f"{float(value):.1f}%"


def kpi_value(kpis: Dict[str, Any], key: str, default: float) -> float:
    try:
        return float(kpis.get(key, default))
    except (TypeError, ValueError):
        return default


def render_metric_card(label: str, value: str, delta: str, tone: str = "neutral") -> None:
    st.markdown(
        f"""
        <div class="metric-card tone-{tone}">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-delta">{delta}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def build_kpi_table(base: Dict[str, Any], disrupted: Dict[str, Any], recovery: Dict[str, Any]) -> pd.DataFrame:
    rows = [
        ("Freight cost", "USD", kpi_value(base, "cost_usd", 0), kpi_value(disrupted, "cost_usd", 0), kpi_value(recovery, "cost_usd", 0)),
        ("Service level", "OTIF %", kpi_value(base, "otif_pct", 0), kpi_value(disrupted, "otif_pct", 0), kpi_value(recovery, "otif_pct", 0)),
        ("CO2 emissions", "kg", kpi_value(base, "co2_kg", 0), kpi_value(disrupted, "co2_kg", 0), kpi_value(recovery, "co2_kg", 0)),
        ("Transit delay", "hours", kpi_value(base, "delay_hours", 0), kpi_value(disrupted, "delay_hours", 0), kpi_value(recovery, "delay_hours", 0)),
    ]
    return pd.DataFrame(rows, columns=["Metric", "Unit", "Baseline", "Disrupted", "Recovery"])


def format_metric_value(metric: str, unit: str, value: float) -> str:
    if unit == "USD":
        return money(value)
    if unit == "OTIF %":
        return pct(value)
    if metric == "CO2 emissions":
        return f"{float(value):,.0f} kg"
    if metric == "Transit delay":
        return f"{float(value):,.1f} hrs"
    return f"{float(value):,.1f}"


def render_html_table(headers: List[str], rows: List[List[str]], class_name: str = "") -> None:
    header_html = "".join(f"<th>{escape(str(header))}</th>" for header in headers)
    row_html = ""
    for row in rows:
        row_html += "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>"

    table_html = (
        f'<div class="html-table-wrap {class_name}">'
        '<table class="html-table">'
        f"<thead><tr>{header_html}</tr></thead>"
        f"<tbody>{row_html}</tbody>"
        "</table>"
        "</div>"
    )
    st.markdown(table_html, unsafe_allow_html=True)


def render_kpi_chart(kpi_df: pd.DataFrame, metric: str, title: str) -> None:
    row = kpi_df[kpi_df["Metric"] == metric].iloc[0]
    states = ["Baseline", "Disrupted", "Recovery"]
    values = [row["Baseline"], row["Disrupted"], row["Recovery"]]
    colors = ["#475569", "#dc2626", "#0f766e"]
    max_value = max([abs(float(value)) for value in values] + [1.0])

    bars = ""
    for state, value, color in zip(states, values, colors):
        numeric_value = float(value)
        width = max(4.0, min(100.0, (abs(numeric_value) / max_value) * 100.0))
        label = format_metric_value(str(row["Metric"]), str(row["Unit"]), numeric_value)
        bars += (
            '<div class="css-chart-row">'
            f'<div class="css-chart-label">{escape(state)}</div>'
            '<div class="css-chart-track">'
            f'<div class="css-chart-bar" style="width:{width:.1f}%; background:{color};"></div>'
            "</div>"
            f'<div class="css-chart-value">{escape(label)}</div>'
            "</div>"
        )

    chart_html = (
        '<div class="css-chart-card">'
        f'<div class="css-chart-title">{escape(title)}</div>'
        f"{bars}"
        "</div>"
    )
    st.markdown(chart_html, unsafe_allow_html=True)


def render_agent_workflow_graph() -> None:
    graph_html = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
  * { box-sizing: border-box; }
  body {
    margin: 0;
    padding: 0;
    background: transparent;
    font-family: Inter, Arial, sans-serif;
    color: #111827;
  }
  .graph {
    width: 100%;
    min-width: 960px;
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 18px;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05);
  }
  .row {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    margin: 12px 0;
  }
  .lane {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
    max-width: 820px;
    margin: 12px auto;
  }
  .node {
    position: relative;
    min-width: 176px;
    min-height: 82px;
    background: #ffffff;
    border: 1px solid #94a3b8;
    border-top: 4px solid #475569;
    border-radius: 8px;
    padding: 12px 13px;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
    transition: transform 140ms ease, box-shadow 140ms ease, border-color 140ms ease;
  }
  .node:hover {
    transform: translateY(-2px);
    border-color: #0f766e;
    box-shadow: 0 8px 18px rgba(15, 23, 42, 0.12);
    z-index: 10;
  }
  .label {
    color: #0f172a;
    font-weight: 800;
    font-size: 15px;
    line-height: 1.15;
    margin-bottom: 5px;
  }
  .caption {
    color: #334155;
    font-size: 12px;
    line-height: 1.35;
    font-weight: 650;
  }
  .tooltip {
    visibility: hidden;
    opacity: 0;
    position: absolute;
    left: 50%;
    bottom: calc(100% + 12px);
    transform: translateX(-50%);
    width: 305px;
    background: #0f172a;
    color: #f8fafc;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 12px 13px;
    box-shadow: 0 16px 30px rgba(15, 23, 42, 0.25);
    font-size: 12px;
    line-height: 1.45;
    pointer-events: none;
    transition: opacity 140ms ease;
  }
  .node:hover .tooltip { visibility: visible; opacity: 1; }
  .arrow {
    color: #475569;
    font-weight: 900;
    font-size: 20px;
    flex: 0 0 auto;
  }
  .down {
    text-align: center;
    color: #475569;
    font-weight: 900;
    font-size: 20px;
    line-height: 1;
    margin: 2px 0;
  }
  .security { border-top-color: #dc2626; }
  .supervisor { border-top-color: #2563eb; }
  .analysis { border-top-color: #b45309; }
  .tool { border-top-color: #0f766e; }
  .evaluation { border-top-color: #7c3aed; }
  .approval { border-top-color: #be123c; }
  .explanation { border-top-color: #0f766e; }
  .memory { border-top-color: #475569; }
</style>
</head>
<body>
<div class="graph">
  <div class="row">
    <div class="node memory">
      <div class="label">Streamlit Dashboard</div>
      <div class="caption">Scenario, severity, planner policy</div>
      <div class="tooltip"><strong>Input surface</strong><br>The planner selects a disruption scenario, severity, and policy preferences. The dashboard writes preferences to memory and starts the recovery workflow.</div>
    </div>
    <div class="arrow">&rarr;</div>
    <div class="node supervisor">
      <div class="label">SupervisorAgent</div>
      <div class="caption">Workflow coordinator</div>
      <div class="tooltip"><strong>SupervisorAgent</strong><br>Creates the execution context, orders specialist agents, and keeps deterministic tools separate from AI reasoning.</div>
    </div>
    <div class="arrow">&rarr;</div>
    <div class="node security">
      <div class="label">SecurityAgent</div>
      <div class="caption">Guardrails and tool RBAC</div>
      <div class="tooltip"><strong>SecurityAgent</strong><br>Checks prompt risk, scenario allowlists, tool permissions, schema safety, hard budget rules, and writes structured audit events.</div>
    </div>
  </div>
  <div class="down">&darr;</div>
  <div class="lane">
    <div class="node analysis">
      <div class="label">DisruptionAgent</div>
      <div class="caption">Affected entity analysis</div>
      <div class="tooltip"><strong>DisruptionAgent</strong><br>Identifies whether the disruption affects routes, warehouses, demand volume, or fleet capacity.</div>
    </div>
    <div class="node analysis">
      <div class="label">DemandAgent</div>
      <div class="caption">Order and customer impact</div>
      <div class="tooltip"><strong>DemandAgent</strong><br>Reviews impacted orders, service exposure, priority, due dates, and customer impact before recovery planning.</div>
    </div>
    <div class="node analysis">
      <div class="label">InventoryAgent</div>
      <div class="caption">Fallback stock feasibility</div>
      <div class="tooltip"><strong>InventoryAgent</strong><br>Checks warehouse inventory, fallback fulfillment options, capacity constraints, and redirection feasibility.</div>
    </div>
  </div>
  <div class="down">&darr;</div>
  <div class="row">
    <div class="node tool">
      <div class="label">TransportAgent</div>
      <div class="caption">Tool-backed recovery plan</div>
      <div class="tooltip"><strong>TransportAgent</strong><br>Calls deterministic tools for First Fit Decreasing truck loading, nearest-neighbor route sequencing, and KPI calculation.</div>
    </div>
    <div class="arrow">&rarr;</div>
    <div class="node tool">
      <div class="label">MCP Tool Layer</div>
      <div class="caption">Schema-gated deterministic tools</div>
      <div class="tooltip"><strong>MCP-compatible tool layer</strong><br>Exposes logistics functions with JSON schemas, role scopes, destructive hints, and permission checks before execution.</div>
    </div>
    <div class="arrow">&rarr;</div>
    <div class="node evaluation">
      <div class="label">EvaluationAgent</div>
      <div class="caption">Baseline vs disrupted vs recovery</div>
      <div class="tooltip"><strong>EvaluationAgent</strong><br>Compares cost, service level, CO2, delay, utilization, trucks used, and recovery quality against planner preferences.</div>
    </div>
  </div>
  <div class="down">&darr;</div>
  <div class="lane">
    <div class="node approval">
      <div class="label">HumanApprovalAgent</div>
      <div class="caption">Policy gate</div>
      <div class="tooltip"><strong>HumanApprovalAgent</strong><br>Blocks automatic dispatch when cost or service thresholds require planner sign-off. Gemini cannot override this gate.</div>
    </div>
    <div class="node evaluation">
      <div class="label">Agentic AI Review</div>
      <div class="caption">Gemini specialist reasoning</div>
      <div class="tooltip"><strong>Agentic AI Specialist Review</strong><br>When Gemini is configured, specialist roles review deterministic KPI outputs, create risk flags, recommend next actions, and explain tradeoffs.</div>
    </div>
    <div class="node memory">
      <div class="label">RL Policy Learner</div>
      <div class="caption">Scenario policy memory</div>
      <div class="tooltip"><strong>ReinforcementLearningAgent</strong><br>Updates contextual-bandit Q-values by scenario and severity from KPI rewards. It learns posture preferences, not route math.</div>
    </div>
  </div>
  <div class="down">&darr;</div>
  <div class="row">
    <div class="node explanation">
      <div class="label">ExplanationAgent</div>
      <div class="caption">Executive recommendation</div>
      <div class="tooltip"><strong>ExplanationAgent</strong><br>Converts trace, KPIs, policy status, and AI specialist review into a manager-ready recommendation.</div>
    </div>
    <div class="arrow">&rarr;</div>
    <div class="node memory">
      <div class="label">Reports and Memory</div>
      <div class="caption">Trace, Markdown, Excel, policy state</div>
      <div class="tooltip"><strong>Outputs</strong><br>Saves session state, agent trace, RL policy updates, audit events, Markdown briefs, and Excel workbooks.</div>
    </div>
  </div>
</div>
</body>
</html>
"""
    components.html(graph_html, height=710, scrolling=True)


def load_dispatch_plan() -> pd.DataFrame:
    orders = data_tools.load_orders()
    warehouses = data_tools.load_warehouses()
    trucks = data_tools.load_trucks()
    dist = data_tools.load_distance_matrix()

    assignments = inventory_tools.assign_orders_to_warehouses(orders, warehouses, dist)
    packed = transport_tools.build_truckloads_ffd(assignments["assignments"], trucks)

    rows: List[Dict[str, Any]] = []
    for truckload in packed.get("truckloads", []):
        allocated = float(truckload.get("allocated_pallets", 0))
        capacity = float(truckload.get("capacity_pallets", 1))
        order_ids = [order.get("order_id", "") for order in truckload.get("orders", [])]
        rows.append(
            {
                "Truck": truckload.get("truck_id"),
                "Home hub": truckload.get("home_warehouse"),
                "Allocated pallets": int(allocated),
                "Capacity": int(capacity),
                "Utilization": round((allocated / capacity) * 100.0, 1) if capacity else 0.0,
                "Carrier": "Spot" if truckload.get("is_external") else "Fleet",
                "Orders": ", ".join(order_ids[:6]) + ("..." if len(order_ids) > 6 else ""),
            }
        )
    return pd.DataFrame(rows)


def latest_report_text() -> str:
    try:
        report_dir = Path(config.BASE_DIR) / "outputs" / "reports"
        reports = [path for path in report_dir.glob("report_*.md") if "test_report" not in path.name]
        if not reports:
            return ""
        latest = max(reports, key=os.path.getmtime)
        return latest.read_text(encoding="utf-8")
    except Exception:
        return ""


def fallback_report(
    session_state: Dict[str, Any],
    scenario_type: str,
    decision: str,
    base: Dict[str, Any],
    disrupted: Dict[str, Any],
    recovery: Dict[str, Any],
) -> str:
    return f"""# Supply Chain Resilience Recovery Report

## Executive Summary
- Session ID: `{session_state.get("session_id", "not-run")}`
- Active scenario: `{scenario_type}`
- Decision status: `{decision}`

The platform compared baseline, disrupted, and recovery operating states, then generated a recovery recommendation using deterministic logistics tools for inventory feasibility, FFD truck loading, route sequencing, and KPI calculation.

## Scorecard
| KPI | Baseline | Disrupted | Recovery |
| :--- | ---: | ---: | ---: |
| Freight cost | {money(base.get("cost_usd", 0))} | {money(disrupted.get("cost_usd", 0))} | {money(recovery.get("cost_usd", 0))} |
| Service level | {pct(base.get("otif_pct", 0))} | {pct(disrupted.get("otif_pct", 0))} | {pct(recovery.get("otif_pct", 0))} |
| CO2 emissions | {recovery.get("co2_kg", 0):,.1f} kg recovery footprint | | |
| Transit delay | {base.get("delay_hours", 0)} hrs | {disrupted.get("delay_hours", 0)} hrs | {recovery.get("delay_hours", 0)} hrs |

## Recommendation
Proceed according to the policy gate shown in the dashboard. Numerical results are generated by deterministic logistics tools; Gemini is used for interpretation, coordination, and executive communication.
"""


STEP_AGENT_DETAILS = {
    "Security Check": (
        "SecurityAgent",
        "Safety and authorization view",
        "Checks whether the request and tool access are allowed before the workflow continues.",
    ),
    "Disruption Analysis": (
        "DisruptionAgent",
        "Network impact view",
        "Identifies the disrupted scenario, severity, and affected supply-chain element.",
    ),
    "Demand Impact Analysis": (
        "DemandAgent",
        "Customer service view",
        "Measures how many orders or customers are exposed to demand and SLA risk.",
    ),
    "Inventory Feasibility check": (
        "InventoryAgent",
        "Fulfillment feasibility view",
        "Checks whether warehouse stock and fallback fulfillment capacity can support the plan.",
    ),
    "Transport Re-routing": (
        "TransportAgent",
        "Execution planning view",
        "Builds truckloads and route sequences using deterministic logistics tools.",
    ),
    "Plan Evaluation": (
        "EvaluationAgent",
        "KPI tradeoff view",
        "Compares measured recovery KPIs such as cost, service, CO2, delay, and utilization.",
    ),
    "Agentic AI Specialist Review": (
        "AgenticAIOrchestrator",
        "Specialist reasoning view",
        "Uses Gemini specialist reviews when configured, otherwise records deterministic role reasoning.",
    ),
    "Plan Verification": (
        "SecurityAgent",
        "Post-plan validation view",
        "Verifies that the generated plan does not violate configured guardrails.",
    ),
    "Human Approval Gate": (
        "HumanApprovalAgent",
        "Governance view",
        "Decides whether the plan can be approved automatically or needs planner sign-off.",
    ),
    "RL Policy Update": (
        "ReinforcementLearningAgent",
        "Learning policy view",
        "Updates scenario-level strategy preference weights from KPI reward signals.",
    ),
    "Explanation Generation": (
        "ExplanationAgent",
        "Executive communication view",
        "Turns trace, KPIs, and approval status into a manager-ready recommendation.",
    ),
}


def summarize_trace_output(output: Any) -> str:
    if output is None:
        return "No detailed output recorded."
    if not isinstance(output, dict):
        return str(output)

    if "specialist_reviews" in output:
        mode = output.get("mode", "specialist_review")
        used = "Gemini specialist reasoning" if output.get("ai_reasoning_used") else "deterministic specialist trace"
        reviews = output.get("specialist_reviews") or []
        review_bits = []
        for review in reviews[:3]:
            review_bits.append(
                f"{review.get('agent', 'Agent')}: {review.get('decision') or review.get('reasoning', 'review recorded')}"
            )
        extra = "; ".join(review_bits) if review_bits else output.get("executive_recommendation", "review recorded")
        return f"{used} via `{mode}`. {extra}"

    keys = [
        "input_validated",
        "tool_permission_validated",
        "role",
        "disruption",
        "severity",
        "orders_evaluated",
        "assignments_made",
        "trucks_packed",
        "total_freight_cost_usd",
        "total_co2_emissions_kg",
        "average_utilization_pct",
        "cost_increase_pct",
        "human_approval_required",
        "status",
        "action",
        "old_value",
        "new_value",
        "explanation",
    ]
    parts = []
    for key in keys:
        if key in output:
            value = output[key]
            if isinstance(value, float):
                value = round(value, 2)
            parts.append(f"{key}: {value}")

    if parts:
        return "; ".join(parts)

    compact_items = list(output.items())[:4]
    return "; ".join(f"{key}: {value}" for key, value in compact_items)


def build_agent_outputs_response(agent_trace: List[Dict[str, Any]]) -> str:
    if not agent_trace:
        return "I do not have a completed execution trace yet. Run a scenario first, then I can explain each agent output from the last run."

    lines = ["Here is what each agent produced in the last run:"]
    for step in agent_trace:
        step_name = step.get("step", "Workflow step")
        agent, view, purpose = STEP_AGENT_DETAILS.get(
            step_name,
            ("Workflow component", "Operational view", TRACE_EXPLANATIONS.get(step_name, "Workflow step.")),
        )
        lines.append(
            f"- {agent} ({step_name}, {step.get('status', 'Unknown')}): {view}. "
            f"{purpose} Output: {summarize_trace_output(step.get('output'))}"
        )

    lines.append(
        "Expected user action: review the KPI scorecard and policy gate. "
        "If the status is pending human approval, the user should approve or reject dispatch; "
        "if it is approved, the user can export the report or rerun with different planner preferences."
    )
    return "\n".join(lines)


def build_agent_point_of_view_response(agent_trace: List[Dict[str, Any]], agentic_review: Dict[str, Any]) -> str:
    review = agentic_review or {}
    reviews = review.get("specialist_reviews") or []
    if reviews:
        lines = ["The clearest agent point-of-view analysis comes from the specialist review layer:"]
        for item in reviews:
            lines.append(
                f"- {item.get('agent', 'Agent')}: {item.get('reasoning', 'No reasoning recorded')} "
                f"Decision: {item.get('decision', 'No decision recorded')}"
            )
        if review.get("executive_recommendation"):
            lines.append(f"Executive recommendation: {review['executive_recommendation']}")
        return "\n".join(lines)

    if agent_trace:
        return (
            "The agent point of view is split across the execution trace. "
            "EvaluationAgent gives the KPI tradeoff analysis, HumanApprovalAgent gives the governance decision, "
            "TransportAgent gives the operational routing/loading view, and ExplanationAgent turns those outputs into the final manager recommendation.\n\n"
            + build_agent_outputs_response(agent_trace)
        )

    return "Run a scenario first, then the assistant can explain the point of view and output of each agent from the execution trace."


def build_project_assistant_response(
    user_input: str,
    scenario_type: str,
    base_kpi: Dict[str, Any],
    disc_kpi: Dict[str, Any],
    rec_kpi: Dict[str, Any],
    decision: str,
    approval_threshold: float,
    default_prefs: Dict[str, Any],
    agent_trace: List[Dict[str, Any]] | None = None,
    agentic_review: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Return a useful deterministic assistant response when Gemini is offline or too generic."""
    query = user_input.lower()
    agent_trace = agent_trace or []
    agentic_review = agentic_review or {}
    base_cost = kpi_value(base_kpi, "cost_usd", 0)
    rec_cost = kpi_value(rec_kpi, "cost_usd", 0)
    cost_delta_pct = ((rec_cost - base_cost) / base_cost * 100.0) if base_cost else 0.0
    rec_otif = kpi_value(rec_kpi, "otif_pct", 0)
    rec_delay = kpi_value(rec_kpi, "delay_hours", 0)
    rec_co2 = kpi_value(rec_kpi, "co2_kg", 0)

    wants_agents = any(term in query for term in ["agent", "agents", "who does what", "roles"])
    wants_workflow = any(term in query for term in ["how", "work", "operate", "software", "project", "architecture", "system"])
    wants_tools = any(term in query for term in ["tool", "engine", "algorithm", "calculation", "ffd", "route", "inventory"])
    wants_approval = any(term in query for term in ["approval", "pending", "why", "policy", "threshold"])
    wants_summary = any(term in query for term in ["summary", "summarize", "status", "current plan", "kpi"])
    wants_ai_truth = any(term in query for term in ["deterministic", "agentic ai", "actually used", "ai tech", "reinforcement", "rl", "learning"])
    wants_last_run = any(term in query for term in ["last run", "last simulation", "last workflow", "what did we do", "outcomes", "outputs"])
    wants_agent_outputs = any(term in query for term in ["every agent", "each agent", "agent output", "outputs of", "output of"])
    wants_point_of_view = any(term in query for term in ["point of view", "analysis", "analyzis", "analyse", "analyze", "which agent gives"])

    if wants_agent_outputs or wants_last_run:
        response = f"""Last run: `{scenario_type}` with final status `{decision}`.

Measured outcomes:
- Baseline cost: {money(base_cost)}
- Disrupted cost: {money(kpi_value(disc_kpi, "cost_usd", 0))}
- Recovery cost: {money(rec_cost)}
- Recovery service level: {pct(rec_otif)}
- Recovery delay: {rec_delay:.1f} hours
- Recovery CO2: {rec_co2:,.0f} kg

{build_agent_outputs_response(agent_trace)}"""
        return {"response": response, "updated_preferences": {}}

    if wants_point_of_view:
        return {
            "response": build_agent_point_of_view_response(agent_trace, agentic_review),
            "updated_preferences": {},
        }

    if wants_agents or wants_workflow:
        response = f"""This project is a supply-chain resilience control tower. A planner chooses a disruption scenario, then the system runs a multi-agent workflow that compares normal operations, the disrupted state, and a recovery plan.

The workflow is:
1. The Streamlit dashboard sends the selected scenario to the workflow.
2. SupervisorAgent coordinates the specialist agents.
3. SecurityAgent checks unsafe input and policy guardrails.
4. DisruptionAgent identifies what part of the network is affected.
5. DemandAgent identifies exposed customer orders and service risk.
6. InventoryAgent checks whether warehouses can fulfill demand from fallback stock.
7. TransportAgent calls deterministic logistics tools for truck loading and route sequencing.
8. EvaluationAgent compares cost, OTIF service level, CO2, delay, and utilization.
9. HumanApprovalAgent checks thresholds such as cost escalation and service target.
10. ExplanationAgent turns the result into an executive recommendation.

The important design point: the agents coordinate decisions and explain tradeoffs, but the numerical logistics calculations come from deterministic tools. For the current `{scenario_type}` run, recovery cost is {money(rec_cost)}, recovery service level is {pct(rec_otif)}, delay is {rec_delay:.1f} hours, CO2 is {rec_co2:,.0f} kg, and the policy status is `{decision}`."""
        return {"response": response, "updated_preferences": {}}

    if wants_ai_truth:
        response = """Honest answer: the logistics calculations are intentionally deterministic, but the project now has a separate agentic AI reasoning layer.

What is deterministic:
- FFD truck loading
- route sequencing
- inventory feasibility
- cost, CO2, delay, utilization, and service calculations
- human approval threshold checks

What is agentic AI:
- Gemini specialist review runs when a real `GEMINI_API_KEY` is configured.
- The AI reviews the deterministic tool outputs as specialist agents: Supervisor, Security, Disruption, Demand, Inventory, Transport, Evaluation, HumanApproval, and Explanation.
- It produces role-specific reasoning, risk flags, next actions, and an executive recommendation.
- If Gemini is not configured, the app clearly marks the mode as deterministic fallback instead of pretending.

Reinforcement learning:
- The project now includes a lightweight RL/contextual-bandit policy learner.
- It learns which recovery posture works best for each scenario/severity: balanced, service_first, cost_guarded, or co2_aware.
- It updates its Q-values from KPI reward after each simulation.
- It does not fake RL route optimization; deterministic logistics tools still compute the actual plan."""
        return {"response": response, "updated_preferences": {}}

    if wants_tools:
        response = """The logistics engine is not a chatbot. It contains deterministic supply-chain logic:

- First Fit Decreasing truck loading packs orders into available trailers.
- Nearest-neighbor route sequencing orders delivery stops.
- Inventory feasibility checks decide whether fallback warehouses can cover demand.
- KPI tools calculate freight cost, service level, delay, utilization, and CO2.
- The evaluation layer compares baseline, disrupted, and recovery states.

Gemini or the local assistant explains the result, but it does not invent the KPI numbers."""
        return {"response": response, "updated_preferences": {}}

    if wants_approval:
        response = f"""The plan is `{decision}` because the recovery plan is checked against planner policy thresholds.

Current policy check:
- Baseline cost: {money(base_cost)}
- Recovery cost: {money(rec_cost)}
- Cost escalation: {cost_delta_pct:+.2f}%
- Approval threshold: {approval_threshold * 100:.0f}%
- Recovery service level: {pct(rec_otif)}
- Service target: {float(default_prefs.get("service_level_target", 0.95)) * 100:.0f}%

If cost escalation exceeds the configured threshold, or service level falls below the target, HumanApprovalAgent routes the plan to planner review instead of auto-approving it."""
        return {"response": response, "updated_preferences": {}}

    if wants_summary:
        response = f"""Current `{scenario_type}` recovery summary:

- Baseline cost: {money(base_cost)}
- Disrupted cost: {money(kpi_value(disc_kpi, "cost_usd", 0))}
- Recovery cost: {money(rec_cost)}
- Recovery service level: {pct(rec_otif)}
- Recovery delay: {rec_delay:.1f} hours
- Recovery CO2: {rec_co2:,.0f} kg
- Decision: `{decision}`

The system produced this by checking inventory feasibility, packing truckloads, sequencing routes, calculating KPIs, and applying the human approval policy gate."""
        return {"response": response, "updated_preferences": {}}

    response = f"""I can help with this project in four useful ways:

1. Explain how the multi-agent workflow operates.
2. Describe each agent and what it contributes.
3. Explain the logistics tools and KPI calculations.
4. Interpret the current recovery plan and why it needs approval.

Current plan snapshot: `{scenario_type}` recovery cost is {money(rec_cost)}, OTIF is {pct(rec_otif)}, delay is {rec_delay:.1f} hours, and status is `{decision}`."""
    return {"response": response, "updated_preferences": {}}


def should_answer_locally(user_input: str) -> bool:
    query = user_input.lower()
    project_terms = [
        "how do you work",
        "how does this software",
        "operate",
        "project",
        "agents",
        "agent",
        "architecture",
        "workflow",
        "what are the agents",
        "explain this",
        "deterministic",
        "agentic ai",
        "actually used",
        "ai tech",
        "reinforcement",
        "rl",
        "last run",
        "last simulation",
        "outputs",
        "outcomes",
        "point of view",
        "analysis",
        "analyzis",
    ]
    return any(term in query for term in project_terms)


st.set_page_config(
    page_title="Supply Chain Resilience Control Tower",
    page_icon="SC",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        html, body, [class*="css"], .stApp {
            font-family: 'Inter', Arial, sans-serif;
        }

        .stApp {
            background: #f6f7fb;
            color: #111827;
        }

        [data-testid="stAppViewContainer"],
        [data-testid="stAppViewContainer"] p,
        [data-testid="stAppViewContainer"] li,
        [data-testid="stAppViewContainer"] label,
        [data-testid="stAppViewContainer"] span,
        [data-testid="stAppViewContainer"] div {
            color: #111827;
        }

        [data-testid="stAppViewContainer"] .stMarkdown,
        [data-testid="stAppViewContainer"] .stMarkdown p {
            color: #111827;
        }

        [data-testid="stAppViewContainer"] button,
        [data-testid="stAppViewContainer"] div[role="button"],
        [data-testid="stAppViewContainer"] [data-baseweb="button"] {
            background: #ffffff !important;
            background-color: #ffffff !important;
            color: #0f172a !important;
            border: 1px solid #94a3b8 !important;
            box-shadow: none !important;
        }

        [data-testid="stAppViewContainer"] button p,
        [data-testid="stAppViewContainer"] button span,
        [data-testid="stAppViewContainer"] [data-baseweb="button"] p,
        [data-testid="stAppViewContainer"] [data-baseweb="button"] span {
            color: #0f172a !important;
            font-weight: 700 !important;
        }

        [data-testid="stAppViewContainer"] button[kind="primary"],
        [data-testid="stAppViewContainer"] .stButton button[kind="primary"],
        [data-testid="stAppViewContainer"] [data-testid="stDownloadButton"] button,
        [data-testid="stAppViewContainer"] [data-testid="stPopover"] button {
            background: #0f766e !important;
            background-color: #0f766e !important;
            color: #ffffff !important;
            border: 1px solid #0f766e !important;
        }

        [data-testid="stAppViewContainer"] button[kind="primary"] p,
        [data-testid="stAppViewContainer"] button[kind="primary"] span,
        [data-testid="stAppViewContainer"] [data-testid="stDownloadButton"] button p,
        [data-testid="stAppViewContainer"] [data-testid="stDownloadButton"] button span,
        [data-testid="stAppViewContainer"] [data-testid="stPopover"] button p,
        [data-testid="stAppViewContainer"] [data-testid="stPopover"] button span {
            color: #ffffff !important;
        }

        [data-testid="stAppViewContainer"] input,
        [data-testid="stAppViewContainer"] textarea,
        [data-testid="stAppViewContainer"] [data-baseweb="input"],
        [data-testid="stAppViewContainer"] [data-baseweb="textarea"],
        [data-testid="stAppViewContainer"] [data-baseweb="select"] > div {
            background: #ffffff !important;
            background-color: #ffffff !important;
            color: #111827 !important;
            border-color: #94a3b8 !important;
        }

        [data-testid="stAppViewContainer"] input::placeholder,
        [data-testid="stAppViewContainer"] textarea::placeholder {
            color: #475569 !important;
        }

        section[data-testid="stSidebar"] {
            background: #101827;
            border-right: 1px solid #1f2937;
        }

        section[data-testid="stSidebar"] * {
            color: #e5e7eb;
        }

        section[data-testid="stSidebar"] [data-baseweb="select"] *,
        section[data-testid="stSidebar"] input,
        section[data-testid="stSidebar"] textarea {
            color: #111827 !important;
        }

        section[data-testid="stSidebar"] button,
        section[data-testid="stSidebar"] [data-baseweb="button"] {
            background: #0f766e !important;
            background-color: #0f766e !important;
            color: #ffffff !important;
            border: 1px solid #14b8a6 !important;
        }

        section[data-testid="stSidebar"] button p,
        section[data-testid="stSidebar"] button span {
            color: #ffffff !important;
        }

        .block-container {
            padding-top: 1.35rem;
            padding-bottom: 2rem;
            max-width: 1440px;
        }

        h1, h2, h3 {
            letter-spacing: 0;
        }

        .top-strip {
            display: flex;
            justify-content: space-between;
            gap: 16px;
            align-items: flex-start;
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 20px 22px;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05);
            margin-bottom: 18px;
        }

        .top-title {
            font-size: 1.85rem;
            line-height: 1.12;
            font-weight: 800;
            color: #0f172a;
            margin: 0;
        }

        .top-subtitle {
            margin: 7px 0 0 0;
            color: #1f2937;
            font-size: 0.98rem;
        }

        .system-badge {
            border: 1px solid #cbd5e1;
            border-radius: 999px;
            padding: 7px 11px;
            color: #0f172a;
            background: #f8fafc;
            font-weight: 700;
            white-space: nowrap;
            font-size: 0.78rem;
        }

        .scenario-band {
            border-left: 5px solid var(--scenario-color);
            background: #ffffff;
            border-radius: 8px;
            padding: 18px 20px;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05);
            margin-bottom: 16px;
        }

        .scenario-band h3 {
            margin: 0 0 6px 0;
            color: #111827;
            font-size: 1.08rem;
        }

        .scenario-band p {
            margin: 0;
            color: #1f2937;
            line-height: 1.45;
        }

        .pill-row {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-top: 12px;
        }

        .pill {
            border-radius: 999px;
            border: 1px solid #d1d5db;
            background: #f9fafb;
            color: #0f172a;
            padding: 5px 10px;
            font-size: 0.78rem;
            font-weight: 700;
        }

        .metric-card {
            background: #ffffff;
            background-color: #ffffff;
            border: 1px solid #e5e7eb;
            border-top: 4px solid #64748b;
            border-radius: 8px;
            padding: 16px;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05);
            min-height: 120px;
        }

        .tone-good { border-top-color: #0f766e; }
        .tone-warn { border-top-color: #b45309; }
        .tone-risk { border-top-color: #dc2626; }
        .tone-neutral { border-top-color: #475569; }

        .metric-label {
            text-transform: uppercase;
            color: #334155;
            font-size: 0.72rem;
            font-weight: 800;
        }

        .metric-value {
            color: #0f172a;
            font-size: 1.55rem;
            line-height: 1.2;
            font-weight: 800;
            margin-top: 8px;
        }

        .metric-delta {
            color: #1f2937;
            font-size: 0.84rem;
            margin-top: 8px;
        }

        .agent-graph {
            background: #ffffff;
            border: 1px solid #cbd5e1;
            border-radius: 8px;
            padding: 18px;
            margin-bottom: 18px;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05);
            overflow-x: auto;
        }

        .agent-graph-stage {
            min-width: 980px;
        }

        .graph-row {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            margin: 12px 0;
        }

        .graph-row.split {
            justify-content: space-between;
        }

        .graph-node {
            position: relative;
            background: #ffffff;
            border: 1px solid #94a3b8;
            border-top: 4px solid #475569;
            border-radius: 8px;
            min-width: 176px;
            max-width: 210px;
            min-height: 78px;
            padding: 12px 13px;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
            transition: transform 140ms ease, box-shadow 140ms ease, border-color 140ms ease;
            cursor: default;
        }

        .graph-node:hover {
            transform: translateY(-2px);
            border-color: #0f766e;
            box-shadow: 0 8px 18px rgba(15, 23, 42, 0.12);
            z-index: 20;
        }

        .node-label {
            color: #0f172a;
            font-weight: 800;
            font-size: 0.93rem;
            line-height: 1.15;
            margin-bottom: 5px;
        }

        .node-caption {
            color: #334155;
            font-size: 0.76rem;
            line-height: 1.35;
            font-weight: 650;
        }

        .node-tooltip {
            visibility: hidden;
            opacity: 0;
            position: absolute;
            left: 50%;
            bottom: calc(100% + 12px);
            transform: translateX(-50%);
            width: 300px;
            background: #0f172a;
            color: #f8fafc !important;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 12px 13px;
            box-shadow: 0 16px 30px rgba(15, 23, 42, 0.25);
            font-size: 0.78rem;
            line-height: 1.45;
            pointer-events: none;
            transition: opacity 140ms ease;
        }

        .node-tooltip strong,
        .node-tooltip span,
        .node-tooltip div {
            color: #f8fafc !important;
        }

        .graph-node:hover .node-tooltip {
            visibility: visible;
            opacity: 1;
        }

        .graph-arrow {
            color: #475569;
            font-weight: 900;
            font-size: 1.15rem;
            flex: 0 0 auto;
        }

        .graph-down {
            text-align: center;
            color: #475569;
            font-weight: 900;
            font-size: 1.15rem;
            line-height: 1;
            margin: 2px 0;
        }

        .graph-lane {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 12px;
            align-items: stretch;
            margin: 12px 0;
        }

        .graph-lane.three {
            grid-template-columns: repeat(3, minmax(0, 1fr));
            max-width: 780px;
            margin-left: auto;
            margin-right: auto;
        }

        .graph-node.security { border-top-color: #dc2626; }
        .graph-node.supervisor { border-top-color: #2563eb; }
        .graph-node.analysis { border-top-color: #b45309; }
        .graph-node.tool { border-top-color: #0f766e; }
        .graph-node.evaluation { border-top-color: #7c3aed; }
        .graph-node.approval { border-top-color: #be123c; }
        .graph-node.explanation { border-top-color: #0f766e; }
        .graph-node.memory { border-top-color: #475569; }

        .decision-panel {
            background: #ffffff;
            background-color: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 18px;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05);
        }

        .decision-title {
            color: #334155;
            font-size: 0.72rem;
            font-weight: 800;
            text-transform: uppercase;
        }

        .decision-value {
            color: #111827;
            font-size: 1.25rem;
            font-weight: 800;
            margin: 6px 0 8px 0;
        }

        .decision-copy {
            color: #1f2937;
            font-size: 0.9rem;
            line-height: 1.45;
        }

        [data-testid="stExpander"] {
            background: #ffffff;
            background-color: #ffffff;
            border: 1px solid #d1d5db;
            border-radius: 8px;
        }

        [data-testid="stExpander"] summary,
        [data-testid="stExpander"] summary p {
            color: #0f172a !important;
            font-weight: 700;
        }

        .html-table-wrap {
            background: #ffffff;
            border: 1px solid #cbd5e1;
            border-radius: 8px;
            overflow-x: auto;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05);
            margin-bottom: 16px;
        }

        .html-table {
            width: 100%;
            border-collapse: collapse;
            color: #111827;
            font-size: 0.9rem;
            background: #ffffff;
        }

        .html-table th {
            background: #e2e8f0;
            color: #0f172a;
            font-weight: 800;
            text-align: left;
            padding: 12px 13px;
            border-bottom: 1px solid #cbd5e1;
            white-space: nowrap;
        }

        .html-table td {
            background: #ffffff;
            color: #111827;
            padding: 11px 13px;
            border-bottom: 1px solid #e5e7eb;
            vertical-align: middle;
        }

        .html-table tr:last-child td {
            border-bottom: 0;
        }

        .html-table tr:nth-child(even) td {
            background: #f8fafc;
        }

        .util-cell {
            min-width: 150px;
        }

        .util-track {
            height: 9px;
            background: #e2e8f0;
            border-radius: 999px;
            overflow: hidden;
            margin-top: 6px;
        }

        .util-bar {
            height: 100%;
            border-radius: 999px;
            background: #0f766e;
        }

        .css-chart-card {
            background: #ffffff;
            border: 1px solid #cbd5e1;
            border-radius: 8px;
            padding: 16px;
            min-height: 245px;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05);
            margin-bottom: 14px;
        }

        .css-chart-title {
            color: #0f172a;
            font-size: 1rem;
            font-weight: 800;
            margin-bottom: 16px;
        }

        .css-chart-row {
            display: grid;
            grid-template-columns: 82px minmax(120px, 1fr) 96px;
            gap: 10px;
            align-items: center;
            margin: 15px 0;
        }

        .css-chart-label,
        .css-chart-value {
            color: #111827;
            font-size: 0.82rem;
            font-weight: 700;
        }

        .css-chart-value {
            text-align: right;
        }

        .css-chart-track {
            height: 18px;
            border-radius: 999px;
            background: #e2e8f0;
            border: 1px solid #cbd5e1;
            overflow: hidden;
        }

        .css-chart-bar {
            height: 100%;
            border-radius: 999px;
            min-width: 4px;
        }

        .assistant-popover-note {
            background: #f8fafc;
            border: 1px solid #d1d5db;
            border-radius: 8px;
            padding: 10px 12px;
            margin-bottom: 10px;
            color: #111827;
            font-size: 0.9rem;
        }

        div[data-testid="stPopoverBody"] {
            min-width: 440px;
            max-width: 560px;
            background: #ffffff !important;
            background-color: #ffffff !important;
            color: #111827 !important;
            border: 1px solid #cbd5e1 !important;
        }

        div[data-testid="stPopoverBody"] *,
        div[data-baseweb="popover"] *,
        div[data-baseweb="popover"] p,
        div[data-baseweb="popover"] span,
        div[data-baseweb="popover"] label {
            color: #111827 !important;
        }

        div[data-baseweb="popover"],
        div[data-baseweb="popover"] > div {
            background: #ffffff !important;
            background-color: #ffffff !important;
        }

        div[data-testid="stChatMessage"] p,
        div[data-testid="stChatMessage"] span,
        div[data-testid="stChatMessage"] div {
            color: #111827 !important;
        }

        div[data-testid="stChatMessage"] {
            background: #ffffff !important;
            background-color: #ffffff !important;
            border: 1px solid #d1d5db !important;
        }

        .stDataFrame, div[data-testid="stTable"] {
            background: #ffffff;
            border-radius: 8px;
        }

        div[data-testid="stChatMessage"] {
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
        }

        @media (max-width: 900px) {
            .top-strip {
                flex-direction: column;
            }
            .agent-graph {
                padding: 12px;
            }
            .agent-graph-stage {
                min-width: 760px;
            }
            .graph-node {
                min-width: 150px;
                max-width: 180px;
            }
            .node-tooltip {
                width: 260px;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)

default_prefs = data_tools.load_planner_preferences()

st.sidebar.title("Control Inputs")
scenario_type = st.sidebar.selectbox(
    "Scenario",
    list(SCENARIOS.keys()),
    format_func=lambda value: SCENARIOS[value]["label"],
    index=0,
)

selected_mechanism = scenario_type
if scenario_type == "custom_generative_prompt":
    st.sidebar.subheader("Custom Scenario")
    user_prompt = st.sidebar.text_area(
        "Disruption concept",
        "Heavy blizzards in Turin block road access to inventory warehouses.",
    )
    selected_mechanism = st.sidebar.selectbox(
        "Engine trigger",
        ["demand_spike", "truck_breakdown", "warehouse_bottleneck", "route_closure"],
        format_func=lambda value: SCENARIOS[value]["label"],
    )
    if st.sidebar.button("Generate Structured Case", width="stretch"):
        fallback_case = {
            "id": "SCEN-CUSTOM",
            "name": "Custom disruption",
            "location": "Turin",
            "description": f"Planner-defined disruption concept: {user_prompt}",
            "difficulty": "Medium",
            "base_delay_hours": 24,
        }
        prompt = f"""
Return one JSON object for an Italian supply-chain disruption.
Use this schema exactly:
{{
  "id": "SCEN-CUSTOM",
  "name": "short operational name",
  "location": "one Italian city",
  "description": "one concise architecture-level explanation",
  "difficulty": "Low, Medium, or High",
  "base_delay_hours": 24
}}
Planner request: {user_prompt}
"""
        st.session_state.custom_scenario = generate_json_with_gemini(prompt, fallback_case)

severity_label = st.sidebar.selectbox("Severity", ["low", "medium", "high"], index=1)

st.sidebar.subheader("Policy Preferences")
min_util = st.sidebar.slider(
    "Minimum truck utilization",
    0.50,
    1.00,
    float(default_prefs.get("min_truck_utilization", 0.85)),
    0.05,
)
max_delay = st.sidebar.slider("Maximum delay days", 1, 5, int(default_prefs.get("max_delay_days", 1)))
cost_priority = st.sidebar.selectbox(
    "Cost priority",
    ["low", "medium", "high"],
    index=["low", "medium", "high"].index(default_prefs.get("cost_priority", "high")),
)
co2_priority = st.sidebar.selectbox(
    "CO2 priority",
    ["low", "medium", "high"],
    index=["low", "medium", "high"].index(default_prefs.get("co2_priority", "medium")),
)
service_target = st.sidebar.slider(
    "Service target",
    0.80,
    1.00,
    float(default_prefs.get("service_level_target", 0.95)),
    0.05,
)
approval_threshold = st.sidebar.slider(
    "Human approval cost threshold",
    0.05,
    0.50,
    float(default_prefs.get("human_approval_required_if_cost_increase_above", 0.15)),
    0.05,
)

run_sim = st.sidebar.button("Run Agent Workflow", type="primary", width="stretch")
if run_sim:
    updated_prefs = {
        "min_truck_utilization": min_util,
        "max_delay_days": max_delay,
        "cost_priority": cost_priority,
        "co2_priority": co2_priority,
        "service_level_target": service_target,
        "human_approval_required_if_cost_increase_above": approval_threshold,
    }
    data_tools.update_planner_preferences(updated_prefs)
    with st.spinner("Running security, disruption, demand, inventory, transport, evaluation, approval, and explanation agents..."):
        try:
            run_simulation(selected_mechanism, severity_label)
            st.success("Workflow complete. KPI memory and reports were refreshed.")
        except Exception as exc:
            st.error(f"Simulation failed: {exc}")

session_state = data_tools.load_session_state()
base_kpi = session_state.get("baseline_kpis") or {}
disc_kpi = session_state.get("disrupted_kpis") or {}
rec_kpi = session_state.get("recovery_kpis") or {}
kpi_df = build_kpi_table(base_kpi, disc_kpi, rec_kpi)
agentic_ai_review = session_state.get("agentic_ai_review") or {}
rl_state = session_state.get("reinforcement_learning") or {}

base_cost = kpi_value(base_kpi, "cost_usd", 0)
rec_cost = kpi_value(rec_kpi, "cost_usd", 0)
cost_increase = ((rec_cost - base_cost) / base_cost) if base_cost else 0.0
approval_required = cost_increase > approval_threshold
decision = "Pending human approval" if approval_required else "Approved"

scenario_info = SCENARIOS[scenario_type].copy()
if scenario_type == "custom_generative_prompt" and "custom_scenario" in st.session_state:
    custom = st.session_state.custom_scenario
    scenario_info = {
        "title": custom.get("name", "Custom disruption"),
        "detail": f"{custom.get('location', 'Italy network')}: {custom.get('description', SCENARIOS[scenario_type]['detail'])}",
    }

severity_colors = {"low": "#0f766e", "medium": "#b45309", "high": "#dc2626"}
scenario_color = severity_colors.get(severity_label, "#b45309")

st.markdown(
    """
    <div class="top-strip">
        <div>
            <h1 class="top-title">Supply Chain Resilience Control Tower</h1>
            <p class="top-subtitle">Multi-agent disruption response with deterministic logistics calculations and policy verification.</p>
        </div>
        <div class="system-badge">Gemini: {gemini_status} | Engine: deterministic tools</div>
    </div>
    """.format(gemini_status="live" if has_live_gemini() else "offline fallback"),
    unsafe_allow_html=True,
)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {
            "role": "assistant",
            "content": "I can explain how this supply-chain resilience platform works, describe each agent, interpret the current recovery KPIs, or explain why a plan needs human approval.",
        }
    ]

assistant_cols = st.columns([2.6, 1])
with assistant_cols[1]:
    with st.popover("Planner assistant", width="stretch"):
        st.markdown(
            '<div class="assistant-popover-note">Ask about the active recovery plan, KPI tradeoffs, or planner policy settings.</div>',
            unsafe_allow_html=True,
        )
        for message in st.session_state.chat_history[-8:]:
            with st.chat_message(message["role"]):
                st.write(message["content"])

        assistant_message = st.text_input(
            "Message",
            key="assistant_message",
            placeholder="Example: explain why this needs approval",
        )
        send_message = st.button("Send", type="primary", width="stretch", key="assistant_send")

        if send_message and assistant_message.strip():
            user_input = assistant_message.strip()
            st.session_state.chat_history.append({"role": "user", "content": user_input})

            fallback_response = build_project_assistant_response(
                user_input,
                scenario_type,
                base_kpi,
                disc_kpi,
                rec_kpi,
                decision,
                approval_threshold,
                default_prefs,
                session_state.get("agent_trace", []),
                session_state.get("agentic_ai_review", {}),
            )
            assistant_prompt = f"""
Return only JSON with this schema:
{{
  "response": "helpful professional response for a logistics planner",
  "updated_preferences": {{}}
}}
Allowed preference keys are:
min_truck_utilization, max_delay_days, cost_priority, co2_priority, service_level_target, human_approval_required_if_cost_increase_above.
You are the project assistant for an Agentic Supply Chain Resilience Platform.
Answer the user's actual question. If they ask how the software works, explain the workflow and agents.
If they ask about agents, list the agents and their responsibilities.
If they ask about KPIs, use the supplied numbers only.
Do not invent KPI numbers. Use only this state:
scenario={scenario_type}
baseline_kpis={base_kpi}
disrupted_kpis={disc_kpi}
recovery_kpis={rec_kpi}
planner_preferences={default_prefs}
agent_trace={session_state.get("agent_trace", [])}
agentic_ai_review={session_state.get("agentic_ai_review", {})}
known_agents=[
  "SupervisorAgent coordinates the workflow",
  "SecurityAgent validates requests and guardrails",
  "DisruptionAgent identifies affected entities",
  "DemandAgent analyzes customer and order impact",
  "InventoryAgent checks stock and warehouse alternatives",
  "TransportAgent calls FFD loading and route sequencing tools",
  "EvaluationAgent compares baseline, disrupted, and recovery KPIs",
  "HumanApprovalAgent checks policy thresholds",
  "ExplanationAgent creates executive recommendations"
]
User query: {user_input}
"""
            if should_answer_locally(user_input):
                result = fallback_response
            else:
                result = generate_json_with_gemini(assistant_prompt, fallback_response)
            assistant_text = str(result.get("response", fallback_response["response"]))
            updates = result.get("updated_preferences") or {}
            if isinstance(updates, dict) and updates:
                allowed_keys = set(default_prefs.keys())
                cleaned_updates = {key: value for key, value in updates.items() if key in allowed_keys}
                if cleaned_updates:
                    data_tools.update_planner_preferences({**default_prefs, **cleaned_updates})
                    assistant_text += f"\n\nApplied preference updates: `{cleaned_updates}`"

            st.session_state.chat_history.append({"role": "assistant", "content": assistant_text})
            st.rerun()

st.markdown(
    f"""
    <div class="scenario-band" style="--scenario-color: {scenario_color};">
        <h3>{scenario_info["title"]}</h3>
        <p>{scenario_info["detail"]}</p>
        <div class="pill-row">
            <span class="pill">Severity: {severity_label.upper()}</span>
            <span class="pill">Engine trigger: {selected_mechanism}</span>
            <span class="pill">Session: {session_state.get("session_id", "not-run")}</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

metric_cols = st.columns(4)
with metric_cols[0]:
    render_metric_card("Recovery cost", money(rec_cost), f"{cost_increase * 100:+.1f}% vs baseline", "warn" if approval_required else "good")
with metric_cols[1]:
    recovery_otif = kpi_value(rec_kpi, "otif_pct", 0)
    render_metric_card("Recovery OTIF", pct(recovery_otif), f"Target {service_target * 100:.0f}%", "good" if recovery_otif >= service_target * 100 else "risk")
with metric_cols[2]:
    render_metric_card("Recovery CO2", f"{kpi_value(rec_kpi, 'co2_kg', 0):,.0f} kg", "Deterministic route KPI", "neutral")
with metric_cols[3]:
    render_metric_card("Delay exposure", f"{kpi_value(rec_kpi, 'delay_hours', 0):,.1f} hrs", f"Limit {max_delay * 24} hrs", "good" if kpi_value(rec_kpi, "delay_hours", 0) <= max_delay * 24 else "risk")

ai_cols = st.columns(2)
with ai_cols[0]:
    ai_mode = agentic_ai_review.get("mode", "not-run")
    ai_used = "Gemini reasoning active" if agentic_ai_review.get("ai_reasoning_used") else "Deterministic fallback"
    render_metric_card("Agentic AI layer", ai_used, f"Mode: {ai_mode}", "good" if agentic_ai_review.get("ai_reasoning_used") else "warn")
with ai_cols[1]:
    rl_update = rl_state.get("update", {})
    rl_choice = rl_state.get("choice", {})
    rl_action = rl_update.get("action", rl_choice.get("action", "not-run"))
    rl_reward = rl_update.get("reward", "n/a")
    render_metric_card("RL policy learner", str(rl_action), f"Latest reward: {rl_reward}", "neutral")

governance_cols = st.columns(2)
with governance_cols[0]:
    render_metric_card("Security layer", "Structured guardrails", "Prompt risk + tool RBAC + audit", "good")
with governance_cols[1]:
    render_metric_card("MCP tool layer", "Schema-gated tools", "Role scopes + destructive hints", "good")

st.subheader("Agent Operating Model")
render_agent_workflow_graph()

left, right = st.columns([2.3, 1])

with left:
    st.subheader("KPI Scorecard")
    kpi_rows = []
    for _, row in kpi_df.iterrows():
        kpi_rows.append(
            [
                escape(str(row["Metric"])),
                escape(str(row["Unit"])),
                escape(format_metric_value(str(row["Metric"]), str(row["Unit"]), float(row["Baseline"]))),
                escape(format_metric_value(str(row["Metric"]), str(row["Unit"]), float(row["Disrupted"]))),
                escape(format_metric_value(str(row["Metric"]), str(row["Unit"]), float(row["Recovery"]))),
            ]
        )
    render_html_table(["Metric", "Unit", "Baseline", "Disrupted", "Recovery"], kpi_rows)

    chart_cols = st.columns(2)
    with chart_cols[0]:
        render_kpi_chart(kpi_df, "Freight cost", "Cost comparison")
        render_kpi_chart(kpi_df, "Service level", "Service-level comparison")
    with chart_cols[1]:
        render_kpi_chart(kpi_df, "CO2 emissions", "CO2 comparison")
        render_kpi_chart(kpi_df, "Transit delay", "Delay comparison")

with right:
    st.subheader("Policy Gate")
    st.markdown(
        f"""
        <div class="decision-panel">
            <div class="decision-title">Final recommendation</div>
            <div class="decision-value">{decision}</div>
            <div class="decision-copy">
                Cost escalation is {cost_increase * 100:+.2f}% against the configured approval threshold of {approval_threshold * 100:.0f}%.
                {"Planner sign-off is required before dispatch." if approval_required else "The plan is inside the configured policy gate."}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("Execution Trace")
    trace_steps = session_state.get("agent_trace") or [
        {"step": "Security Check", "status": "Ready"},
        {"step": "Disruption Analysis", "status": "Ready"},
        {"step": "Demand Impact Analysis", "status": "Ready"},
        {"step": "Inventory Feasibility check", "status": "Ready"},
        {"step": "Transport Re-routing", "status": "Ready"},
        {"step": "Plan Evaluation", "status": "Ready"},
        {"step": "Plan Verification", "status": "Ready"},
        {"step": "Explanation Generation", "status": "Ready"},
    ]
    for step in trace_steps:
        with st.expander(f"{step.get('step', 'Agent step')} - {step.get('status', 'Unknown')}", expanded=False):
            st.caption(TRACE_EXPLANATIONS.get(step.get("step"), "Specialized workflow step."))
            if step.get("output") is not None:
                st.json(step["output"])

st.subheader("Recovery Dispatch Plan")
try:
    dispatch_df = load_dispatch_plan()
    if dispatch_df.empty:
        st.info("Run the workflow to populate dispatch assignments.")
    else:
        dispatch_rows = []
        for _, row in dispatch_df.iterrows():
            utilization = float(row["Utilization"])
            dispatch_rows.append(
                [
                    escape(str(row["Truck"])),
                    escape(str(row["Home hub"])),
                    escape(str(row["Allocated pallets"])),
                    escape(str(row["Capacity"])),
                    (
                        f'<div class="util-cell">{utilization:.1f}%'
                        f'<div class="util-track"><div class="util-bar" style="width:{max(0.0, min(100.0, utilization)):.1f}%;"></div></div></div>'
                    ),
                    escape(str(row["Carrier"])),
                    escape(str(row["Orders"])),
                ]
            )
        render_html_table(
            ["Truck", "Home hub", "Allocated pallets", "Capacity", "Utilization", "Carrier", "Orders"],
            dispatch_rows,
            "dispatch-table",
        )
except Exception as exc:
    st.info(f"Dispatch plan is not available yet: {exc}")

st.subheader("Export Brief")
report_content = latest_report_text()
if not report_content:
    report_content = fallback_report(session_state, scenario_type, decision, base_kpi, disc_kpi, rec_kpi)

with st.expander("View executive report", expanded=False):
    st.markdown(report_content)

export_cols = st.columns(2)
with export_cols[0]:
    st.download_button(
        label="Download markdown report",
        data=report_content,
        file_name=f"mitigation_executive_report_{scenario_type}.md",
        mime="text/markdown",
        width="stretch",
    )
with export_cols[1]:
    try:
        from tools.report_tools import generate_excel_report

        dispatch_df = load_dispatch_plan()
        truckloads = []
        if not dispatch_df.empty:
            orders = data_tools.load_orders()
            trucks = data_tools.load_trucks()
            dist = data_tools.load_distance_matrix()
            assignments = inventory_tools.assign_orders_to_warehouses(orders, data_tools.load_warehouses(), dist)
            truckloads = transport_tools.build_truckloads_ffd(assignments["assignments"], trucks).get("truckloads", [])
        excel_bytes = generate_excel_report(
            session_state.get("session_id", "not-run"),
            base_kpi,
            disc_kpi,
            rec_kpi,
            truckloads,
        )
        st.download_button(
            label="Download Excel workbook",
            data=excel_bytes,
            file_name=f"mitigation_executive_report_{scenario_type}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )
    except Exception as exc:
        st.error(f"Excel export unavailable: {exc}")
