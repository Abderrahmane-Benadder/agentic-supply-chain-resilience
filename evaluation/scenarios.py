"""
Scenario presets for testing multi-agent resilience actions.
"""

from typing import Dict, Any, List

SCENARIO_PRESETS: List[Dict[str, Any]] = [
    {
        "id": "SCEN-001",
        "name": "Rome Termini Station Outage",
        "location": "Rome",
        "description": "Power grid failure at Rome rail hub blocks distribution of fresh goods.",
        "difficulty": "Medium",
        "base_delay_hours": 36
    },
    {
        "id": "SCEN-002",
        "name": "Naples Port Strike",
        "location": "Naples",
        "description": "Sudden dockworkers protest halts container unloading in Naples.",
        "difficulty": "High",
        "base_delay_hours": 72
    },
    {
        "id": "SCEN-003",
        "name": "Piedmont Alps Flood",
        "location": "Turin",
        "description": "Landslide on highway A4 blocks transport corridors near Turin.",
        "difficulty": "Low",
        "base_delay_hours": 12
    }
]

def get_scenario_by_id(scenario_id: str) -> Dict[str, Any]:
    """Find scenario info by ID."""
    for s in SCENARIO_PRESETS:
        if s["id"] == scenario_id:
            return s
    raise ValueError(f"Scenario ID {scenario_id} not recognized.")
