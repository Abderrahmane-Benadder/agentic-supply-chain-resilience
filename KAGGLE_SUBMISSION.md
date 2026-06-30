# Kaggle Submission Draft

## Title
Agentic Supply Chain Resilience Platform

## Track
Agents for Business

## Short Pitch
This project is an AI-agent control tower for supply-chain disruption response. A planner selects a disruption scenario, the system runs a structured multi-agent workflow, deterministic logistics tools calculate recovery KPIs, and Gemini/ADK agents explain the operational tradeoffs and approval decision.

## Problem
Supply-chain planners must respond quickly to disruptions such as demand spikes, fleet breakdowns, warehouse bottlenecks, and route closures. Manual replanning is slow, hard to audit, and often mixes business judgment with spreadsheet calculations. This project separates those responsibilities: AI agents coordinate and explain decisions, while deterministic tools calculate the logistics outcomes.

## What The System Does
1. User selects a disruption scenario in the Streamlit dashboard or ADK agent.
2. SupervisorAgent coordinates specialist agents.
3. SecurityAgent validates prompt safety and tool permissions.
4. DisruptionAgent identifies affected entities.
5. DemandAgent assesses customer/service impact.
6. InventoryAgent checks warehouse feasibility.
7. TransportAgent invokes logistics tools for First Fit Decreasing truck loading and route sequencing.
8. EvaluationAgent compares baseline, disrupted, and recovery KPIs.
9. HumanApprovalAgent applies planner policy thresholds.
10. ExplanationAgent generates the final executive recommendation.

## Why This Is Agentic
The project uses agents for coordination, delegation, explanation, governance, and tool orchestration. It does not ask the LLM to invent logistics numbers. Gemini reasons over measured outputs, while deterministic tools calculate inventory feasibility, truck utilization, route sequencing, costs, service level, delay, and CO2.

## Google ADK Usage
- Official `google-adk` app in `adk_app/agent.py`.
- ADK `root_agent` named `supply_chain_resilience_supervisor`.
- Specialist ADK sub-agents for security, disruption, demand, inventory, transport, evaluation, human approval, and explanation.
- ADK tool binding through `adk_app/tools.py`.
- ADK callbacks initialize state and enforce role-based tool authorization.
- ADK FastAPI app is available through `adk_app/fast_api_app.py`.

## Course Concept Mapping
- Multi-Agent Systems: implemented through supervisor and specialist agents.
- Tool Usage: implemented through deterministic logistics tools.
- MCP-style Interoperability: lightweight JSON-RPC local tool layer with schemas and RBAC.
- Memory / State: planner preferences, session state, execution trace, and RL policy memory.
- Security Guardrails: prompt-risk checks, role authorization, policy validation, audit logs.
- Evaluation: baseline/disrupted/recovery KPI comparison, pytest suite, and ADK eval assets.
- Human-in-the-Loop: policy thresholds route high-risk plans to planner approval.
- Business Impact: operational response for logistics disruption recovery.

## Demo Script
Use the Streamlit dashboard:

```bash
python -m streamlit run app.py --server.port 8505
```

Suggested demo:
1. Select `route_closure` with high severity.
2. Run the workflow.
3. Show the KPI scorecard, dispatch plan, execution trace, visual agent graph, and final recommendation.
4. Ask the chatbot: `How does this system work and why does this plan need human approval?`
5. Export the Markdown or Excel report.

Use the ADK agent:

```bash
adk run adk_app "Run a high severity route_closure recovery and explain whether dispatch needs human approval."
```

## Suggested Kaggle Writeup Assets
- Screenshot of the full dashboard after a scenario run.
- Screenshot of the visual agent graph with hover details.
- Screenshot of the KPI scorecard and final approval status.
- Screenshot or terminal capture of `adk run adk_app`.
- Short demo video or GIF showing scenario selection, workflow run, chatbot explanation, and report export.

## Required Kaggle Submission Checklist
- Kaggle Writeup under 2,500 words.
- Track selected: **Agents for Business**.
- Media Gallery cover image attached.
- Public YouTube video attached to the Media Gallery, 5 minutes or less.
- Public Project Link attached.
- Public GitHub repository attached if the live demo is not enough.
- No API keys, passwords, or private credentials in the public codebase.

## Required Course Concepts Demonstrated
The competition asks for at least three course concepts. This project demonstrates more than three:

| Required Concept | Where It Appears |
| :--- | :--- |
| Agent / Multi-agent system (ADK) | `adk_app/agent.py`, ADK `root_agent`, 8 specialist sub-agents |
| MCP Server | `mcp_server/server.py`, `mcp_server/tool_registry.py` as a lightweight MCP-inspired local tool layer |
| Antigravity | Mention and show the Antigravity IDE / project workflow in the demo video |
| Security features | `security/guardrails.py`, `agents/security_agent.py`, audit logs, RBAC tool checks |
| Deployability | Live Cloud Run URL and `DEPLOYMENT.md` |
| Agent skills / Agents CLI | `skills/`, `AGENTS.md`, `agents-cli-manifest.yaml`, `tests/eval/` |

## Links To Include In Kaggle
- GitHub repository: `https://github.com/Abderrahmane-Benadder/agentic-supply-chain-resilience`
- Live Cloud Run URL: `https://supply-chain-resilience-xxzkv6nlxa-ue.a.run.app`
- Optional demo video: `ADD_VIDEO_URL`

When opening the Cloud Run URL, select the `adk_app` app in the ADK web UI before sending a prompt.

## Reproducibility Commands
```bash
pip install --user -r requirements.txt
python -m pytest
python -m streamlit run app.py --server.port 8505
adk run adk_app "Explain the agent architecture."
```

## Honest Scope Notes
- The MCP layer is MCP-inspired/local, not claimed as full official MCP server compliance.
- Reinforcement learning is scoped to contextual-bandit policy learning, not deep route optimization.
- Cloud deployment is optional; the capstone prototype is runnable locally and ADK-ready.
