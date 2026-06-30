# Architecture Graph

This file gives a visual map of how the project is divided and how the main runtime paths work.

## 1. System Workflow

```mermaid
flowchart TD
    User[Planner / Judge / User]

    User --> Streamlit[Streamlit Dashboard<br/>app.py]
    User --> ADKWeb[Cloud Run ADK Web UI<br/>adk_app.fast_api_app]

    Streamlit --> MainPipeline[Simulation Pipeline<br/>main.py]
    ADKWeb --> ADKRoot[ADK root_agent<br/>supply_chain_resilience_supervisor]

    ADKRoot --> ADKTools[ADK Tool Wrappers<br/>adk_app/tools.py]
    ADKRoot --> SubAgents[ADK Specialist Sub-agents]

    SubAgents --> SecurityAgent[SecurityAgent]
    SubAgents --> DisruptionAgent[DisruptionAgent]
    SubAgents --> DemandAgent[DemandAgent]
    SubAgents --> InventoryAgent[InventoryAgent]
    SubAgents --> TransportAgent[TransportAgent]
    SubAgents --> EvaluationAgent[EvaluationAgent]
    SubAgents --> HumanApprovalAgent[HumanApprovalAgent]
    SubAgents --> ExplanationAgent[ExplanationAgent]

    MainPipeline --> ClassicAgents[Dashboard Agent Classes<br/>agents/]
    ADKTools --> MainPipeline

    MainPipeline --> SecurityLayer[Guardrails + Audit<br/>security/]
    ADKRoot --> SecurityLayer

    MainPipeline --> LogisticsTools[Deterministic Logistics Tools<br/>tools/]
    ADKTools --> LogisticsTools

    LogisticsTools --> DataLayer[CSV Logistics Data<br/>data/]
    MainPipeline --> MemoryLayer[Memory / State<br/>memory/]
    ADKRoot --> MemoryLayer

    LogisticsTools --> KPIs[Baseline / Disrupted / Recovery KPIs]
    KPIs --> Approval[Human Approval Gate]
    Approval --> Recommendation[Executive Recommendation]

    Recommendation --> DashboardResults[Dashboard Results + Exports]
    Recommendation --> ADKResponse[ADK Agent Response]
```

## 2. Repository Structure

```mermaid
flowchart LR
    Repo[agentic-supply-chain-resilience]

    Repo --> UI[Frontend / Dashboard]
    UI --> AppPy[app.py<br/>Streamlit planner UI]
    UI --> StreamlitConfig[.streamlit/config.toml]

    Repo --> ADK[Official Google ADK App]
    ADK --> ADKAgent[adk_app/agent.py<br/>root_agent + sub-agents]
    ADK --> ADKTools[adk_app/tools.py<br/>ADK tool wrappers]
    ADK --> ADKFastAPI[adk_app/fast_api_app.py<br/>Cloud Run FastAPI app]
    ADK --> ADKUtils[adk_app/app_utils/]

    Repo --> AgentLayer[Agent Logic]
    AgentLayer --> AgentFiles[agents/<br/>supervisor, security, disruption,<br/>demand, inventory, transport,<br/>evaluation, approval, explanation, RL]

    Repo --> ToolLayer[Deterministic Tool Layer]
    ToolLayer --> Tools[tools/<br/>data, disruption, inventory,<br/>transport, evaluation, reports]
    ToolLayer --> MCP[mcp_server/<br/>MCP-inspired JSON-RPC tools]

    Repo --> Safety[Security]
    Safety --> Guardrails[security/guardrails.py]
    Safety --> Audit[security/audit_log.py]

    Repo --> Data[Data + Memory]
    Data --> CSV[data/*.csv<br/>Italy logistics network]
    Data --> DemoData[data/generate_demo_data.py]
    Data --> Memory[memory/<br/>planner prefs + RL policy]

    Repo --> Eval[Evaluation]
    Eval --> Pytest[tests/<br/>unit/integration tests]
    Eval --> ADKEval[tests/eval/<br/>agents-cli eval dataset/config]
    Eval --> Metrics[evaluation/<br/>scenario + KPI metrics]

    Repo --> Deploy[Deployment + Submission]
    Deploy --> Docker[Dockerfile + .dockerignore]
    Deploy --> Cloud[deployment/<br/>Terraform / CI scaffold]
    Deploy --> Docs[README.md<br/>DEPLOYMENT.md<br/>KAGGLE_SUBMISSION.md]
```

## 3. Local vs Cloud Runtime

```mermaid
flowchart TD
    Local[Local Machine]
    Cloud[Google Cloud]
    Kaggle[Kaggle Submission]

    Local --> StreamlitRun[python -m streamlit run app.py]
    StreamlitRun --> Dashboard[Planner-facing Streamlit dashboard]
    Dashboard --> LocalPipeline[main.py deterministic simulation]

    Local --> ADKRun[adk run adk_app]
    ADKRun --> LocalADK[Local ADK Gemini agent]

    Cloud --> CloudRun[Cloud Run service]
    CloudRun --> FastAPI[adk_app.fast_api_app]
    FastAPI --> ADKWeb[ADK web/API interface]
    ADKWeb --> CloudADK[Deployed ADK root_agent]

    CloudADK --> Gemini[Gemini model]
    CloudADK --> DeterministicTools[Deterministic logistics tools]
    LocalADK --> Gemini
    LocalADK --> DeterministicTools
    LocalPipeline --> DeterministicTools

    Kaggle --> Writeup[Kaggle Writeup]
    Kaggle --> Media[Media Gallery + YouTube Video]
    Kaggle --> RepoLink[Public GitHub Repository]
    Kaggle --> LiveLink[Cloud Run ADK Link]
```

## 4. Responsibility Boundary

```mermaid
flowchart LR
    Gemini[Gemini / LLM]
    Agents[Agent Coordination]
    Engine[Deterministic Logistics Engine]
    Governance[Human + Security Governance]

    Gemini --> Agents
    Agents --> Engine
    Agents --> Governance

    Gemini --> LLMTasks[Reasoning<br/>risk interpretation<br/>delegation<br/>business explanations<br/>executive summaries]
    Engine --> EngineTasks[First Fit Decreasing loading<br/>nearest-neighbor sequencing<br/>inventory feasibility<br/>cost / CO2 / delay / service KPIs]
    Governance --> GovTasks[Prompt safety<br/>RBAC tool permissions<br/>audit logs<br/>human approval thresholds]
```

## 5. Competition Evidence Map

This architecture is designed to show that the project is more than a chatbot wrapper. Each layer provides evidence for a specific AI Agents Capstone requirement.

| Evidence | What It Demonstrates |
| --- | --- |
| Streamlit dashboard | A business-facing recovery planning interface with scenario selection, KPIs, tables, execution trace, chatbot popover, and an agent workflow graph. |
| ADK agent backend | Official Google ADK usage for defining the agent entrypoint, managing sessions, and exposing the deployed agent through the ADK runtime interface. |
| Multi-agent workflow | Specialized agents coordinate security, disruption analysis, demand impact, inventory feasibility, transport recovery, evaluation, approval, and final explanation. |
| Tool layer | Agents call deterministic logistics tools instead of asking the LLM to invent operational numbers. |
| Deterministic logistics engine | Truck loading, route sequencing, inventory feasibility, service level, cost, utilization, and CO2 calculations are handled by code. |
| Security and governance | The workflow includes request validation, tool permission checks, audit logging, and human approval thresholds. |
| Evaluation assets | Tests and evaluation files support repeatable validation instead of only relying on a live demo. |
| Cloud Run deployment | The ADK service is deployed to Google Cloud, making the backend accessible outside the local development environment. |

For a Kaggle submission, this diagram can be used in the writeup and video to explain how Gemini, ADK agents, local tools, deterministic logistics logic, and the Streamlit interface work together.
