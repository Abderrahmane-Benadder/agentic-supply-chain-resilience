# Agentic Supply Chain Resilience Platform

### **Track: Agents for Business**
*An official Google ADK multi-agent platform for logistics disruption response, recovery planning, and policy verification.*

---

## 1. Project Title
**Agentic Supply Chain Resilience Platform**

---

## 2. Track
**Agents for Business** - Specialized in automating operational crisis management, logistics rerouting, and compliance verification.

---

## 3. Problem Statement
Global supply chain operations are subject to sudden, unpredictable disruptions: flash flooding, labor strikes, warehouse throughput outages, and mechanical fleet breakdowns. Traditionally, correcting these delays requires hours of manual rescheduling by logistics planners, leading to SLA breaches, high spot carrier premiums, and inflated carbon footprints.

---

## 4. Why This is a Real Business Problem
Supply chains operate on razor-thin margins. A single late delivery can trigger financial penalties, customer escalations, or lost trust. Manual mitigation lacks real-time coordination across:
- **Inventory levels** (Is fallback stock available?)
- **Fleet capacities** (Can we pack excess loads without unnecessary spot carrier surcharges?)
- **Carbon accounting** (What is the impact of rerouting on CO2 targets?)
- **Corporate policies** (Does the recovery cost exceed the budget threshold?)

This platform automates the decision workflow and measures the results through the generated baseline, disrupted, and recovery KPI scorecards.

---

## 5. Architecture
The platform is designed with a **three-tier architecture** separating the user interface, the agent orchestration layer, and the deterministic logistics tools:

```text
Streamlit Web Dashboard
        |
        | 1. User selects a disruption or enters a custom planner prompt
        v
SupervisorAgent
        |
        +--> SecurityAgent
        +--> DisruptionAgent
        +--> DemandAgent
        +--> InventoryAgent
        +--> TransportAgent
        +--> EvaluationAgent
        +--> HumanApprovalAgent policy gate
        +--> ExplanationAgent
        |
        | 2. Tool calls and KPI calculations
        v
Lightweight MCP-inspired Tool Layer
        |
        | 3. Reads and writes operational data
        v
CSV Database: Italy logistics network
```

The architecture intentionally separates reasoning, policy coordination, and calculations. Agents coordinate the workflow and explain tradeoffs; the logistics engine performs the numerical operations.

The repository now includes an official Google ADK app under [adk_app/](adk_app/). The ADK `root_agent` is the supply-chain supervisor, binds the deterministic logistics tools, exposes specialist sub-agents, initializes session state, and applies the same guardrail layer used by the dashboard workflow.

The main simulation path now includes two explicit intelligence layers after deterministic recovery KPIs are produced:
- **Agentic AI Specialist Review:** When a valid `GEMINI_API_KEY` is configured, Gemini reviews the deterministic tool outputs through specialist-agent roles and returns role-specific reasoning, risk flags, next actions, and an executive recommendation. If Gemini is unavailable, the system records a deterministic fallback trace instead of overstating AI usage.
- **ReinforcementLearningAgent:** A lightweight contextual-bandit policy learner updates scenario/severity Q-values after each simulation. It learns whether `balanced`, `service_first`, `cost_guarded`, or `co2_aware` recovery posture performs best under observed KPI rewards.

# How the System Works
The workflow starts in the Streamlit control tower and proceeds through a structured multi-agent recovery pipeline:

1. **User selects a disruption scenario in the Streamlit dashboard.** The planner chooses demand spike, truck breakdown, warehouse bottleneck, route closure, or a custom generated scenario.
2. **SupervisorAgent receives the request.** It standardizes the request, creates the execution context, and coordinates the specialist agents.
3. **SecurityAgent validates the request and tool permissions.** It checks for unsafe prompt patterns, validates allowed tool usage, and records guardrail events in the audit log.
4. **DisruptionAgent identifies affected entities.** It determines whether the scenario impacts orders, lanes, warehouses, fleet assets, or capacity.
5. **DemandAgent analyzes customer impact and prioritization.** It identifies exposed orders and frames the service-level risk that the recovery plan must address.
6. **InventoryAgent evaluates inventory feasibility and warehouse alternatives.** It checks whether available stock and warehouse capacity can support fallback fulfillment.
7. **TransportAgent calls logistics tools to generate a recovery plan.** It invokes deterministic tools for First Fit Decreasing truck loading and nearest-neighbor route sequencing.
8. **EvaluationAgent compares baseline, disrupted, and recovery KPIs.** It computes cost, service-level, CO2, delay, and utilization metrics across the three operating states.
9. **HumanApprovalAgent verifies policy thresholds.** The policy gate checks planner preferences such as cost escalation limits and service-level targets before a plan is approved.
10. **ExplanationAgent generates the final executive recommendation.** Gemini is used to turn the trace, KPIs, and policy status into a manager-ready recommendation.
11. **Results are displayed and exported.** The dashboard shows the scorecard, dispatch plan, execution trace, approval status, Markdown report, and Excel workbook.

# Why AI Agents?
This project uses agents because disruption response is a coordination problem, not a single logistics formula.

- **Separation of responsibilities:** Security, disruption analysis, demand impact, inventory feasibility, transport recovery, evaluation, approval, and explanation are handled by distinct specialist roles.
- **Modular decision making:** Each agent can be improved or replaced without rewriting the whole recovery workflow.
- **Explainability:** The execution trace shows which agent acted, what it produced, and how the final recommendation was formed.
- **Tool orchestration:** Agents decide when to call logistics tools, but the tools perform the operational calculations.
- **Human-in-the-loop governance:** Cost and service thresholds produce an approval gate rather than silently dispatching every plan.
- **Business flexibility:** Planner preferences and scenario definitions can change without changing the deterministic route and inventory engine.

Agents coordinate decisions and business reasoning. They do not directly perform mathematical optimization; deterministic logistics tools perform the calculations used in the KPI scorecards.

This project intentionally avoids letting the LLM invent operational numbers. Agentic AI is used for specialist review, risk interpretation, governance explanation, and executive recommendation. The logistics engine remains deterministic so the scorecard is auditable.

# LLM Responsibilities vs Logistics Engine Responsibilities
All numerical calculations come from deterministic tools and not from the LLM. Gemini is used for interpretation, coordination, explanation, and recommendation generation.

| Gemini / LLM Responsibilities | Deterministic Logistics Engine Responsibilities |
| :--- | :--- |
| Disruption interpretation | First Fit Decreasing truck loading |
| Workflow coordination | Nearest-neighbor route sequencing |
| Agent delegation | Inventory feasibility calculations |
| Risk analysis | Service-level calculations |
| Business tradeoff explanations | Utilization calculations |
| Executive summaries | Cost calculations |
| Recommendation generation | CO2 calculations |

| Learning / Policy Responsibilities | Scope |
| :--- | :--- |
| Scenario/severity policy learning | Lightweight contextual-bandit Q-value updates |
| Recovery posture selection | Chooses among `balanced`, `service_first`, `cost_guarded`, `co2_aware` |
| Reward calculation | Uses deterministic KPI outcomes |
| Not included | Deep RL route optimization or learned numerical KPI generation |

---

## 6. Agents and Their Roles

| Agent Name | Core Role & Responsibilities |
| :--- | :--- |
| **SupervisorAgent** | Coordinates the entire recovery workflow. Delegates to specialists and compiles final decisions. |
| **SecurityAgent** | Sanitizes user prompts, enforces cost caps, blocks unsafe commands, and records audit logs. |
| **DisruptionAgent** | Classifies active outages such as weather disruptions, strikes, breakdowns, and route closures. |
| **DemandAgent** | Identifies at-risk customer orders and prioritizes them by operational exposure. |
| **InventoryAgent** | Queries warehouse stock balances and evaluates stock reallocation alternatives. |
| **TransportAgent** | Packs trucks using FFD bin packing and sequences routes using nearest-neighbor routing. |
| **EvaluationAgent** | Scores recovery KPIs against organizational preferences and targets. |
| **HumanApprovalAgent** | Applies policy thresholds for cost escalation, service targets, and manual review requirements. |
| **ExplanationAgent** | Translates plan metrics into natural-language executive briefings for managers. |

---

## 7. ADK Usage
The platform uses the official **Google Agent Development Kit (ADK)** through the `google-adk` package. The ADK entrypoint is [adk_app/agent.py](adk_app/agent.py), where `root_agent` defines the runnable supply-chain supervisor agent.

In this implementation:
- **Agent definitions:** `root_agent` and the specialist sub-agents are official ADK `Agent` objects.
- **Workflow orchestration:** The ADK supervisor coordinates security, disruption, demand, inventory, transport, evaluation, human approval, and explanation roles.
- **Session and state management:** ADK session state is initialized from `memory/session_state.json` and planner preferences, while the deterministic workflow persists the latest KPI state for dashboard and agent reuse.
- **Tool binding:** ADK tools in [adk_app/tools.py](adk_app/tools.py) wrap the logistics engine, dataset validation, planner policy updates, architecture explanation, and RBAC checks.
- **Guardrail callbacks:** The ADK app uses a `before_tool_callback` to apply role-based tool authorization before tool execution.
- **Specialized coordination:** Gemini provides reasoning, delegation, risk interpretation, and executive communication while logistics tools perform calculations.
- **Agentic specialist review:** `AgenticAIOrchestrator` calls Gemini for specialist-agent reasoning when live credentials are available and records whether AI reasoning was actually used.

Gemini does not generate operational KPI numbers. Gemini reasons over measured outputs from deterministic tools such as First Fit Decreasing loading, nearest-neighbor route sequencing, inventory feasibility, service-level evaluation, cost calculation, and CO2 calculation.

---

## 8. Lightweight MCP-inspired Tool Layer Usage
The project exposes the core logistics solvers and datasets as callable tools under [mcp_server/server.py](mcp_server/server.py). The current implementation should be understood as a **Lightweight MCP-inspired Tool Layer** rather than a claim of full official MCP SDK compliance.

- **Core exposed tools:** `validate_dataset`, `simulate_disruption`, `check_inventory_feasibility`, `assign_orders_to_warehouses`, `build_truckloads_ffd`, `sequence_route_nearest_neighbor`, and `calculate_transport_kpis`.
- **Local interoperability pattern:** The server implements a stdio JSON-RPC 2.0 message handler that represents a local MCP-compatible tool abstraction for capstone demonstration purposes.
- **Operational value:** Agents can treat logistics capabilities as tools with explicit inputs and outputs instead of embedding calculations inside prompts.
- **Schema enforcement:** Tool calls are validated against generated JSON schemas, including required arguments, rejected unknown arguments, and basic type checks.
- **Security annotations:** Tool definitions include category, destructive-operation hints, and required role scopes.
- **Permission gateway:** Tool execution is checked against role-based access rules before deterministic logistics functions are called.

---

## 9. Skills Implementation
Specialist agents leverage modular, reusable markdown instruction profiles under [skills/](skills/):
- **`demand_analysis_skill.md`**: Procedural steps for calculating late SLA impact.
- **`inventory_feasibility_skill.md`**: Standard guidelines for checking stock levels.
- **`transport_recovery_skill.md`**: Packing heuristics instructions.
- **`evaluation_skill.md`**: Formal business preference scoring procedures.

---

## 10. Memory / Session / State
- **Planner Preferences (`planner_preferences.json`)**: Persistent memory parameters for truck utilization, delay tolerance, service target, cost priority, CO2 priority, and human approval threshold.
- **Session State (`session_state.json`)**: Tracks execution variables such as KPIs, active scenario, selected severity, planner preferences, and the complete agent step-by-step trace.
- **RL Policy (`rl_policy.json`)**: Stores learned Q-values for scenario/severity recovery postures based on KPI reward.

---

## 11. Security Features
- **Structured prompt-risk analysis:** Detects prompt injection, command/SQL injection, credential leakage, possible PII, and oversized prompts.
- **Role-based tool authorization:** Enforces viewer, planner, simulator, and admin permission boundaries for MCP-style tool calls.
- **Scenario and dataset allowlists:** Restricts disruption simulation and dataset access to known safe demo domains.
- **Plan guardrails:** Checks whether recovery cost escalation, invalid action structure, or hard budget violations require blocking or human review.
- **Policy-clamped AI recommendations:** Gemini specialist reviews cannot override the deterministic HumanApprovalAgent gate.
- **Audit logs:** Records input validation, tool authorization, schema failures, tool calls, and guardrail violations in [security/audit.log](security/audit.log).

---

## 12. Evaluation Framework
The evaluation layer compares plans across:
- **Baseline:** Normal operating state before disruption.
- **Disrupted state:** Operating state after the selected scenario changes demand, capacity, fleet availability, or route access.
- **Recovery plan:** Replanned state after inventory checks, truck loading, route sequencing, and policy evaluation.

The system generates a final scorecard based on measured variances in freight cost, service level, CO2 emissions, and delay exposure. Approval status is derived from the current planner policy thresholds rather than hard-coded claims.

The reinforcement-learning component updates a lightweight policy after each run. Its reward function favors service recovery and penalizes excess cost, delay, CO2 increase, and human-approval friction. This is intentionally scoped as policy learning, not as a replacement for deterministic route planning.

The repository also includes ADK/agents-cli evaluation assets:
- [tests/eval/datasets/basic-dataset.json](tests/eval/datasets/basic-dataset.json) contains agent-behavior prompts for architecture explanation, recovery execution, and security boundaries.
- [tests/eval/eval_config.yaml](tests/eval/eval_config.yaml) defines response-quality, safety, and calculation-boundary grounding checks.

Run:

```bash
agents-cli eval generate
agents-cli eval grade
```

These evals complement the deterministic pytest suite. Pytest validates tool contracts and logistics calculations; agents-cli eval validates agent behavior, response quality, tool trajectory, and safety posture. The local `adk run` smoke test works with the AI Studio API key path; the full `agents-cli eval generate` / `grade` workflow uses the Vertex evaluation stack and requires Google Cloud Application Default Credentials plus a project configured in the environment.

---

## 13. Demo Scenarios
1. **Demand Spike:** Sudden market demand spikes order volumes, threatening warehouse overcapacity.
2. **Truck Breakdown:** Fleet vehicle breakdown requires trailer reallocation.
3. **Warehouse Bottleneck:** Major logistics hub outage requires order redirections to Bologna.
4. **Route Closure:** Highway closure requires alternate lane sequencing and recovery KPI evaluation.

---

## 14. How to Run Locally

### **Step 1: Install Dependencies**
```bash
pip install --user -r requirements.txt
```

### **Step 2: Setup Environments**
Create a `.env` file in the project root:
```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

### **Step 3: Run the Streamlit Dashboard**
```bash
python -m streamlit run app.py --server.port 8505
```

### **Step 4: Run the Official ADK Agent**
```bash
adk run adk_app
```

If `adk` is not on your PATH after a user-level Windows install, run it from:
```bash
C:\Users\aben5\AppData\Roaming\Python\Python312\Scripts\adk.exe run adk_app
```

Example prompt:
```text
Run a high severity route_closure recovery and explain whether dispatch needs human approval.
```

### **Submission and Deployment Guides**
- Kaggle writeup draft: [KAGGLE_SUBMISSION.md](KAGGLE_SUBMISSION.md)
- Google Cloud deployment guide: [DEPLOYMENT.md](DEPLOYMENT.md)
- Live Cloud Run ADK service: https://supply-chain-resilience-xxzkv6nlxa-ue.a.run.app

---

## 15. Demo Walkthrough
A strong judging demo can be completed with one scenario run:

1. Start the Streamlit dashboard and select **Route Closure** with **High** severity.
2. Run the workflow and review the baseline, disrupted, and recovery KPI scorecards.
3. Open the visual agent workflow graph to show the specialist-agent sequence and hover details.
4. Check the execution trace to verify SecurityAgent, TransportAgent, EvaluationAgent, HumanApprovalAgent, and ExplanationAgent activity.
5. Open the chatbot popover and ask: `How does this system work and why does this plan need human approval?`
6. Export the Markdown or Excel report for the final executive recommendation.
7. Run the same scenario through ADK with:

```bash
adk run adk_app "Run a high severity route_closure recovery and explain whether dispatch needs human approval."
```

The expected demonstration point is not a fixed KPI claim. The point is that the system measures the baseline, disrupted, and recovery states dynamically, applies policy thresholds, and explains whether the recovery plan is approved or pending human review.

---

## 16. ADK Verification
The ADK layer can be verified independently from the Streamlit dashboard:

```bash
agents-cli info
python -c "from adk_app.agent import app, root_agent; print(app.name, root_agent.name, len(root_agent.tools), len(root_agent.sub_agents))"
python -m pytest
```

For a live Gemini-backed ADK smoke test:

```bash
adk run adk_app "Explain the agent architecture and the boundary between Gemini reasoning and deterministic logistics tools."
```

On Windows, if `adk` is not on PATH after a user-level install:

```bash
C:\Users\aben5\AppData\Roaming\Python\Python312\Scripts\adk.exe run adk_app "Explain the agent architecture and the boundary between Gemini reasoning and deterministic logistics tools."
```

---

## 17. Example Outputs
- **Markdown report:** Saves a structured executive brief in `outputs/reports/`.
- **Excel report workbook:** Compiles multi-sheet styled worksheets (`KPI Scorecard`, `Vehicle Dispatches`, and `Audit Trails`) in `.xlsx` format for corporate downloads.
- **Visual trace logs:** Renders the specialist-agent execution trace directly in the Streamlit UI.

---

## 18. Limitations
- **Symmetric distances:** Relies on symmetric pairwise demo distances rather than live traffic feeds.
- **Single disruption:** Models one primary crisis scenario per session.
- **Heuristic recovery:** Uses practical dispatch heuristics rather than a full mixed-integer optimization solver.

---

# Logistics Intelligence
This platform is not a generic chatbot wrapped around supply-chain text. It embeds logistics intelligence through deterministic tools and structured data:

- **First Fit Decreasing truck loading** for pallet-to-truck allocation.
- **Capacity constraints** for available fleet and external carrier fallback.
- **Warehouse inventory feasibility checks** before redirecting demand.
- **Disruption recovery heuristics** for demand spikes, truck breakdowns, warehouse bottlenecks, and route closures.
- **Route sequencing** using nearest-neighbor delivery ordering.
- **Service-level evaluation** comparing baseline, disrupted, and recovery states.

AI agents coordinate these capabilities, decide which tools to invoke, apply policy gates, and explain tradeoffs. Deterministic algorithms perform the operational calculations used in the final recommendation.

---

## 19. Future Work
- **Live Traffic API:** Connect to Google Maps API for real-time traffic detour costs.
- **Multi-Hub Routing:** Extend FFD heuristics to support complex multi-warehouse drop-shipping.
- **Richer evaluation datasets:** Add a broader set of disruption scenarios and human-approval edge cases.

---

# Submission Checklist
- Confirm `.env` is not submitted with a real API key.
- Run `python -m pytest` and confirm the test suite passes.
- Run `agents-cli eval generate` and `agents-cli eval grade` for at least the included smoke eval dataset after configuring Google Cloud Application Default Credentials.
- Run `agents-cli info` and confirm the agent directory is `adk_app`.
- Run the Streamlit dashboard once and verify the KPI panels, tables, execution trace, chatbot popover, and agent graph render correctly.
- Run one ADK smoke test with `adk run adk_app` or the absolute Windows `adk.exe` path.
- Include screenshots or a short demo video showing the dashboard, visual agent workflow graph, KPI scorecard, exported report, and ADK command output.

---

# Course Concept Alignment
This project maps the 5-day AI Agents course concepts to a concrete business workflow:

| Course / Challenge Concept | Project Evidence | Alignment |
| :--- | :--- | :--- |
| Agent foundations | Supervisor plus specialist agents for security, disruption, demand, inventory, transport, evaluation, approval, and explanation | Implemented |
| Google ADK | Official `google-adk` app in [adk_app/agent.py](adk_app/agent.py), `root_agent`, sub-agents, callbacks, and tools | Implemented |
| Tool usage | ADK tools wrap simulation, dataset validation, policy preferences, security checks, KPI state, and architecture explanation | Implemented |
| MCP / interoperability | Local JSON-RPC tool layer with schemas, RBAC, annotations, and audit logs | MCP-inspired local abstraction |
| Multi-agent systems | ADK sub-agents and dashboard trace show coordinated specialist responsibilities | Implemented |
| Context / state / memory | Planner preferences, session state, execution trace, and RL policy memory persist in JSON files | Implemented |
| Security and safety | Prompt-risk checks, command-injection detection, role-based tool authorization, output policy checks, and audit logging | Implemented |
| Human-in-the-loop | HumanApprovalAgent gates cost/service threshold breaches before dispatch approval | Implemented |
| Evaluation | Deterministic KPI comparison, pytest suite, and ADK eval dataset/config under `tests/eval/` | Implemented |
| Observability | Execution traces, audit logs, exported reports, ADK FastAPI surface, and optional telemetry hooks | Partially implemented for local demo |
| Production deployment | `agents-cli` manifest, ADK FastAPI app, Dockerfile, and scaffolded CI/Terraform assets are present; cloud deployment target is intentionally set to `none` for capstone prototype | Prototype-ready, not production-deployed |
| A2A / external agent interoperability | Not implemented as a live A2A service; project uses internal multi-agent coordination and MCP-style local tools instead | Out of scope |

The project is deliberately honest about scope: it demonstrates official ADK, tools, memory/state, security, evaluation, and human approval in a runnable capstone prototype without claiming full production deployment, full official MCP compliance, or A2A service publishing.

---

# Why This Fits the Kaggle AI Agents Capstone
- &#10003; **Multi-Agent Systems:** Supervisor, Security, Disruption, Demand, Inventory, Transport, Evaluation, Human Approval, and Explanation roles coordinate a complete business workflow.
- &#10003; **Google ADK:** The project includes an official `google-adk` app with `adk_app/agent.py`, ADK `Agent` definitions, bound tools, sub-agent coordination, session-state initialization, and tool guardrail callbacks.
- &#10003; **Tool Usage:** Agents call explicit logistics tools for inventory, routing, transport KPI calculation, evaluation, reporting, and security checks.
- &#10003; **MCP-style Interoperability:** The local JSON-RPC tool layer exposes deterministic logistics capabilities through a lightweight MCP-inspired abstraction.
- &#10003; **Agent Skills:** Markdown skill files define reusable specialist operating procedures for demand, inventory, transport, and evaluation.
- &#10003; **Memory / State:** Planner preferences and execution state persist across runs through JSON memory.
- &#10003; **Security Guardrails:** Input sanitization, output validation, policy thresholds, and audit logging are built into the workflow.
- &#10003; **Evaluation Framework:** The system compares baseline, disrupted, and recovery KPIs and surfaces the approval decision.
- &#10003; **Human-in-the-Loop Decision Making:** Recovery plans that exceed policy thresholds are routed to planner approval instead of being automatically accepted.
- &#10003; **Real Business Impact:** The application targets a concrete operational problem: faster, more explainable supply-chain disruption response with measurable cost, service, delay, and CO2 tradeoffs.
