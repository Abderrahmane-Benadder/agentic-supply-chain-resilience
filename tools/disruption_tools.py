"""
Tools for query and simulation of logistics disruptions (e.g. weather, labor strikes, port closures).
"""

from typing import List, Dict, Any, Optional
import random
import pandas as pd
from tools import data_tools

# Mock feed database representing potential external events
MOCK_DISRUPTIONS = [
    {
        "disruption_id": "DIS-001",
        "type": "Weather",
        "location": "Rome",
        "severity": "High",
        "description": "Severe storms causing flash floods and roadway blockages",
        "active": True,
        "eta_clear_days": 2
    },
    {
        "disruption_id": "DIS-002",
        "type": "Labor Strike",
        "location": "Naples",
        "severity": "Critical",
        "description": "Port workers strike blocking container processing terminal",
        "active": True,
        "eta_clear_days": 5
    },
    {
        "disruption_id": "DIS-003",
        "type": "Accident",
        "location": "Turin",
        "severity": "Low",
        "description": "Accident on A4 highway causing slow freight traffic",
        "active": False,
        "eta_clear_days": 0
    }
]

def check_active_disruptions(location: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Check the feed for currently active disruptions.
    
    Args:
        location: Optional filter for a specific city.
    """
    active = [d for d in MOCK_DISRUPTIONS if d["active"]]
    if location:
        active = [d for d in active if location.lower() in d["location"].lower()]
    return active

def trigger_disruption_event(disruption_id: str) -> Dict[str, Any]:
    """
    Simulate activating or setting a disruption to active.
    """
    for d in MOCK_DISRUPTIONS:
        if d["disruption_id"] == disruption_id:
            d["active"] = True
            return {"status": "success", "triggered": d}
    return {"status": "error", "message": f"Disruption ID {disruption_id} not found"}

def simulate_demand_spike(severity: float) -> Dict[str, Any]:
    """
    Simulate a market demand spike by increasing order pallet sizes.
    
    Args:
        severity: Percentage spike multiplier (e.g. 0.3 means +30% orders volume).
    """
    if not (0.0 <= severity <= 1.0):
        return {"status": "error", "message": "Severity must be between 0.0 and 1.0"}
        
    try:
        df = data_tools.load_dataset("orders")
        original_sum = int(df["pallets"].sum())
        
        # Increase and cap at standard maximum pallet scale if desired, say 33 pallets
        df["pallets"] = df["pallets"].apply(lambda p: min(33, max(1, int(round(p * (1.0 + severity))))))
        new_sum = int(df["pallets"].sum())
        
        data_tools.save_dataset("orders", df)
        
        return {
            "status": "success",
            "simulation": "demand_spike",
            "severity": severity,
            "original_total_pallets": original_sum,
            "new_total_pallets": new_sum,
            "net_increase": new_sum - original_sum
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def simulate_truck_breakdown(truck_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Disable a truck's availability status representing a breakdown.
    
    Args:
        truck_id: Specific truck ID. If None, breaks down a random available truck.
    """
    try:
        df = data_tools.load_dataset("trucks")
        
        # Make sure available column acts as strings or booleans cleanly
        if truck_id:
            idx_list = df[df["truck_id"] == truck_id].index
            if len(idx_list) == 0:
                return {"status": "error", "message": f"Truck {truck_id} not found"}
            idx = idx_list[0]
        else:
            # Pick a random truck that is currently available
            avail_mask = df["available"].astype(str).str.lower() == "true"
            avail_idx = df[avail_mask].index
            if len(avail_idx) == 0:
                return {"status": "error", "message": "No available trucks to break down"}
            idx = random.choice(avail_idx)
            truck_id = str(df.at[idx, "truck_id"])
            
        df.at[idx, "available"] = False
        data_tools.save_dataset("trucks", df)
        
        return {
            "status": "success",
            "simulation": "truck_breakdown",
            "truck_id": truck_id,
            "details": f"Truck {truck_id} availability set to False."
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def simulate_warehouse_bottleneck(warehouse_id: str, capacity_reduction_percent: float) -> Dict[str, Any]:
    """
    Reduce a warehouse's daily throughput capacity by a bottleneck factor.
    
    Args:
        warehouse_id: Target warehouse (e.g. WH-MILAN).
        capacity_reduction_percent: Percent decrease (e.g. 0.40 means 40% reduction).
    """
    if not (0.0 <= capacity_reduction_percent <= 1.0):
        return {"status": "error", "message": "Reduction must be between 0.0 and 1.0"}
        
    try:
        df = data_tools.load_dataset("warehouses")
        idx_list = df[df["warehouse_id"] == warehouse_id].index
        if len(idx_list) == 0:
            return {"status": "error", "message": f"Warehouse {warehouse_id} not found"}
            
        idx = idx_list[0]
        original_limit = int(df.at[idx, "daily_throughput_limit"])
        new_limit = int(round(original_limit * (1.0 - capacity_reduction_percent)))
        
        df.at[idx, "daily_throughput_limit"] = new_limit
        data_tools.save_dataset("warehouses", df)
        
        return {
            "status": "success",
            "simulation": "warehouse_bottleneck",
            "warehouse_id": warehouse_id,
            "original_throughput_limit": original_limit,
            "new_throughput_limit": new_limit
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def simulate_route_closure(origin: str, destination: str) -> Dict[str, Any]:
    """
    Mark a shipping route segment as closed by scaling travel time/distance.
    
    Args:
        origin: Start city.
        destination: Destination city.
    """
    try:
        df = data_tools.load_dataset("distance_matrix")
        
        # Check directions (since the matrix is symmetric, update both directions)
        mask = (
            ((df["origin"].str.lower() == origin.lower()) & (df["destination"].str.lower() == destination.lower())) |
            ((df["origin"].str.lower() == destination.lower()) & (df["destination"].str.lower() == origin.lower()))
        )
        
        if df[mask].empty:
            return {"status": "error", "message": f"Route segment {origin} <-> {destination} not found"}
            
        # Simulate closure by setting travel time to a large delay factor (e.g. 999.0 hours)
        df.loc[mask, "travel_time_hours"] = 999.0
        data_tools.save_dataset("distance_matrix", df)
        
        return {
            "status": "success",
            "simulation": "route_closure",
            "origin": origin,
            "destination": destination,
            "new_travel_time_hours": 999.0
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
