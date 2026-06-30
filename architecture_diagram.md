# 📐 System Architecture Diagram

This file details the structural and data flow architecture of the **Agentic Supply Chain Resilience Platform**.

---

## 1. Unified Node Flow Diagram

```mermaid
graph TD
    User([User / Streamlit Dashboard]) -->|1. Scenario & Preferences| Supervisor[Supervisor Agent]
    
    subgraph Multi-Agent Layer (Google ADK Core)
        Supervisor -->|2. Sanitise Input| Security[Security Agent]
        Security -->|3. Pass Validation| Disruption[Disruption Agent]
        Disruption -->|4. Get Impacted Items| Demand[Demand Agent]
        Demand -->|5. Redirect Stock| Inventory[Inventory Agent]
        Inventory -->|6. Pack & Route Heuristics| Transport[Transport Agent]
        Transport -->|7. Score Performance| Evaluation[Evaluation Agent]
        Evaluation -->|8. Generate Narrative Brief| Explanation[Explanation Agent]
    end

    subgraph Tooling Layer (MCP-Style Tools)
        Disruption -->|check_active_disruptions| MCP_Server
        Demand -->|get_order_by_id| MCP_Server
        Inventory -->|check_inventory_feasibility| MCP_Server
        Transport -->|build_truckloads_ffd| MCP_Server
        Transport -->|sequence_route_nearest_neighbor| MCP_Server
        Evaluation -->|calculate_transport_kpis| MCP_Server
    end

    subgraph Storage & Audit Logs
        MCP_Server -->|Read CSVs| DataFiles[(Italy Logistics Database)]
        Security -->|Audit Logs| AuditFile[(security/audit.log)]
        Evaluation -->|Preference Memory| PrefFile[(planner_preferences.json)]
        Supervisor -->|Session Tracking| SessionFile[(session_state.json)]
    end
```

---

## 2. Component Explanations

1. **User Interface (Streamlit Dashboard)**:
   Planners configure operational preferences and select or generate crisis scenarios.
2. **Orchestrator (Supervisor Agent)**:
   Standardizes ADK agent execution, delegating sub-tasks sequentially and tracking execution state.
3. **Guardrails Gateway (Security Agent)**:
   Monitors input queries and verifies output costs to ensure safety guidelines are never breached.
4. **Logistics Tool Registry (MCP-Style Server)**:
   Standardizes local mathematical routing algorithms and database connections as RPC-callable tools.
5. **Memory and State Managers (JSON Storage)**:
   Ensures that planner configurations persist across execution runs and session histories are preserved.
