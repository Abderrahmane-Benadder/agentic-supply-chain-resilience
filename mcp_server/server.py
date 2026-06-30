"""
MCP-Style Local Tool Server for Capstone Demonstration.
Exposes supply chain logistics, routing, inventory allocation, and disruption tools.
"""

import sys
import json
from typing import Dict, Any, List
from mcp_server.tool_registry import registry
from tools import (
    data_tools,
    disruption_tools,
    inventory_tools,
    transport_tools,
    evaluation_tools,
    report_tools
)

# 1. Register validate_dataset
@registry.register(
    name="validate_dataset",
    description="Validate supply chain CSV datasets (orders, warehouses, trucks, suppliers, distance_matrix).",
    scopes=["viewer", "planner", "simulator"],
    category="data_quality",
)
def validate_dataset(name: str) -> Dict[str, Any]:
    return data_tools.validate_dataset(name)

# 2. Register simulate_disruption (Combined Dispatcher Tool)
@registry.register(
    name="simulate_disruption",
    description="Simulate standard logistics disruption events: demand_spike, truck_breakdown, warehouse_bottleneck, or route_closure.",
    scopes=["simulator"],
    destructive=True,
    category="simulation",
)
def simulate_disruption(scenario_type: str, severity: float = 0.35, target_id: str = "") -> Dict[str, Any]:
    """Exposes a single dispatcher tool to apply various disruptions."""
    if scenario_type == "demand_spike":
        return disruption_tools.simulate_demand_spike(severity)
    elif scenario_type == "truck_breakdown":
        return disruption_tools.simulate_truck_breakdown(target_id if target_id else None)
    elif scenario_type == "warehouse_bottleneck":
        return disruption_tools.simulate_warehouse_bottleneck(target_id if target_id else "WH-MILAN", severity)
    elif scenario_type == "route_closure":
        # Standard route closure targets Milan and Rome in Italy demo
        return disruption_tools.simulate_route_closure("Milan", "Rome")
    else:
        return {"status": "error", "message": f"Unknown disruption type: {scenario_type}"}

# 3. Register check_inventory_feasibility
@registry.register(
    name="check_inventory_feasibility",
    description="Evaluate if warehouses have enough total stock to cover active orders.",
    scopes=["planner", "simulator"],
    category="inventory",
)
def check_inventory_feasibility(orders: List[Dict[str, Any]], warehouses: List[Dict[str, Any]]) -> Dict[str, Any]:
    return inventory_tools.check_inventory_feasibility(orders, warehouses)

# 4. Register assign_orders_to_warehouses
@registry.register(
    name="assign_orders_to_warehouses",
    description="Assign pending orders to the nearest warehouse containing inventory capacity.",
    scopes=["planner", "simulator"],
    category="inventory",
)
def assign_orders_to_warehouses(
    orders: List[Dict[str, Any]], 
    warehouses: List[Dict[str, Any]], 
    distance_matrix: List[Dict[str, Any]]
) -> Dict[str, Any]:
    return inventory_tools.assign_orders_to_warehouses(orders, warehouses, distance_matrix)

# 5. Register build_truckloads_ffd
@registry.register(
    name="build_truckloads_ffd",
    description="Pack orders into standard 33-pallet mega-trailers using First-Fit Decreasing (FFD) bin packing.",
    scopes=["planner", "simulator"],
    category="transport",
)
def build_truckloads_ffd(orders: List[Dict[str, Any]], trucks: List[Dict[str, Any]]) -> Dict[str, Any]:
    return transport_tools.build_truckloads_ffd(orders, trucks)

# 6. Register sequence_route_nearest_neighbor
@registry.register(
    name="sequence_route_nearest_neighbor",
    description="Sequence delivery locations within a truckload using Traveling Salesperson nearest-neighbor routing.",
    scopes=["planner", "simulator"],
    category="transport",
)
def sequence_route_nearest_neighbor(truckload: Dict[str, Any], distance_matrix: List[Dict[str, Any]]) -> Dict[str, Any]:
    return transport_tools.sequence_route_nearest_neighbor(truckload, distance_matrix)

# 7. Register calculate_transport_kpis
@registry.register(
    name="calculate_transport_kpis",
    description="Calculate consolidated transport KPIs (total distance, hours, costs, CO2 emissions).",
    scopes=["planner", "simulator"],
    category="evaluation",
)
def calculate_transport_kpis(
    plan: List[Dict[str, Any]], 
    trucks: List[Dict[str, Any]], 
    distance_matrix: List[Dict[str, Any]]
) -> Dict[str, Any]:
    return transport_tools.calculate_transport_kpis(plan, trucks, distance_matrix)

# 8. Register compare_baseline_disrupted_recovery
@registry.register(
    name="compare_baseline_disrupted_recovery",
    description="Contrast KPI scorecards side-by-side between baseline, disrupted, and recovery states.",
    scopes=["viewer", "planner", "simulator"],
    category="evaluation",
)
def compare_baseline_disrupted_recovery(
    baseline: Dict[str, Any], 
    disrupted: Dict[str, Any], 
    recovery: Dict[str, Any]
) -> Dict[str, Any]:
    return evaluation_tools.compare_baseline_disrupted_recovery(baseline, disrupted, recovery)

# 9. Register generate_manager_summary
@registry.register(
    name="generate_manager_summary",
    description="Compile a narrative executive summary explaining supply chain mitigations.",
    scopes=["viewer", "planner", "simulator"],
    category="reporting",
)
def generate_manager_summary(results: Dict[str, Any]) -> Dict[str, Any]:
    return report_tools.generate_manager_summary(results)


def run_stdio_server():
    """
    Standard input/output JSON-RPC handler for MCP clients.
    Exposes list_tools and call_tool protocols.
    """
    print("Agentic Supply Chain MCP-Style Tool Server running on stdio...", file=sys.stderr)
    print("Listening for JSON-RPC messages (e.g. methods: tools/list or tools/call)...", file=sys.stderr)

    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            
            message = json.loads(line)
            msg_id = message.get("id")
            method = message.get("method")
            params = message.get("params", {})

            if method == "tools/list":
                # Expose list of MCP schemas
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "tools": registry.get_all_tool_definitions()
                    }
                }
            elif method == "tools/call":
                tool_name = params.get("name")
                tool_args = params.get("arguments", {})
                context = params.get("context", {"role": "simulator"})
                
                try:
                    result = registry.call_tool(tool_name, tool_args, context=context)
                    response = {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": json.dumps(result)
                                }
                            ]
                        }
                    }
                except Exception as ex:
                    response = {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "error": {
                            "code": -32603,
                            "message": str(ex)
                        }
                    }
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method {method} not found"
                    }
                }
            
            # Print JSON response to stdout
            print(json.dumps(response))
            sys.stdout.flush()
        except KeyboardInterrupt:
            break
        except Exception as e:
            # Handle unparsed messages
            err_resp = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32700,
                    "message": f"Parse error: {str(e)}"
                }
            }
            print(json.dumps(err_resp))
            sys.stdout.flush()

if __name__ == "__main__":
    # If run directly, launch the tool server
    run_stdio_server()
