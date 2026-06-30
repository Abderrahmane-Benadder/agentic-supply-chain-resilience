"""
Tools for analyzing transport routes, truck status, packing algorithms, routing sequencing, and KPIs.
"""

from typing import Dict, Any, List, Optional
import pandas as pd
from tools import data_tools

def find_available_trucks(location: str) -> List[Dict[str, Any]]:
    """
    Search for trucks currently flagged as available at a given warehouse city location.
    """
    try:
        df = data_tools.load_dataset("trucks")
        is_avail = df["available"].astype(str).str.lower() == "true"
        at_loc = df["home_warehouse"].str.lower().str.contains(location.lower())
        available_trucks = df[is_avail & at_loc]
        return available_trucks.to_dict(orient="records")
    except Exception:
        return []

def calculate_route_cost_and_time(source: str, destination: str, weight_tons: float) -> Dict[str, Any]:
    """
    Find distance in matrix and calculate time & cost of freight.
    """
    try:
        df = data_tools.load_dataset("distance_matrix")
        route = df[
            ((df["origin"].str.lower() == source.lower()) & (df["destination"].str.lower() == destination.lower())) |
            ((df["origin"].str.lower() == destination.lower()) & (df["destination"].str.lower() == source.lower()))
        ]
        
        if route.empty:
            distance_km = 400.0
            estimated_hours = 6.0
        else:
            row = route.iloc[0]
            distance_km = float(row["distance_km"])
            estimated_hours = float(row["travel_time_hours"])
            
        freight_cost = (distance_km * 1.50) + (weight_tons * 20.0)
        
        return {
            "status": "success",
            "source": source,
            "destination": destination,
            "distance_km": distance_km,
            "estimated_hours": estimated_hours,
            "cost_usd": round(freight_cost, 2)
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def assign_truck_to_route(truck_id: str, new_location: str) -> Dict[str, Any]:
    """
    Assign a truck to a route, changing available status to False.
    """
    try:
        df = data_tools.load_dataset("trucks")
        idx_list = df[df["truck_id"] == truck_id].index
        if len(idx_list) == 0:
            return {"status": "error", "message": f"Truck {truck_id} not found"}
        
        idx = idx_list[0]
        df.at[idx, "available"] = False
        data_tools.save_dataset("trucks", df)
        
        return {
            "status": "success",
            "truck_id": truck_id,
            "new_status": "Unavailable (dispatched)",
            "current_location": new_location
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def build_truckloads_ffd(
    orders: List[Dict[str, Any]], 
    trucks: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    First-Fit Decreasing (FFD) bin packing algorithm.
    Packs orders into trucks according to their capacity (e.g. 33 pallets).
    """
    # Sort orders by pallets descending
    sorted_orders = sorted(orders, key=lambda x: int(x.get("pallets", 0)), reverse=True)
    
    # Track available trucks (sorted by capacity descending)
    available_trucks = [t for t in trucks if str(t.get("available")).lower() == "true"]
    # Fallback to external carriers if we exceed fleet capacity
    external_truck_index = 1
    
    packed_trucks: List[Dict[str, Any]] = []
    
    for o in sorted_orders:
        pallets_needed = int(o.get("pallets", 0))
        placed = False
        
        # Try to fit into already active packed trucks
        for pt in packed_trucks:
            if pt["remaining_capacity"] >= pallets_needed:
                pt["orders"].append(o)
                pt["allocated_pallets"] += pallets_needed
                pt["remaining_capacity"] -= pallets_needed
                placed = True
                break
                
        if not placed:
            # Try to assign a new fleet truck
            if available_trucks:
                trk = available_trucks.pop(0)
                capacity = int(trk.get("capacity_pallets", 33))
                packed_trucks.append({
                    "truck_id": trk["truck_id"],
                    "capacity_pallets": capacity,
                    "home_warehouse": trk.get("home_warehouse", "Unknown"),
                    "cost_per_km": float(trk.get("cost_per_km", 1.50)),
                    "co2_kg_per_km": float(trk.get("co2_kg_per_km", 0.82)),
                    "orders": [o],
                    "allocated_pallets": pallets_needed,
                    "remaining_capacity": capacity - pallets_needed,
                    "is_external": False
                })
            else:
                # Assign to external carrier truck
                capacity = 33
                packed_trucks.append({
                    "truck_id": f"TRK-EXT-{external_truck_index:02d}",
                    "capacity_pallets": capacity,
                    "home_warehouse": "EXTERNAL",
                    "cost_per_km": 2.20,  # 45% surcharge for spot contract carrier
                    "co2_kg_per_km": 0.95, # potentially older or unoptimized external truck
                    "orders": [o],
                    "allocated_pallets": pallets_needed,
                    "remaining_capacity": capacity - pallets_needed,
                    "is_external": True
                })
                external_truck_index += 1
                
    return {
        "status": "success",
        "truckloads": packed_trucks,
        "total_trucks_used": len(packed_trucks),
        "fleet_trucks_used": sum(1 for pt in packed_trucks if not pt["is_external"]),
        "external_trucks_used": sum(1 for pt in packed_trucks if pt["is_external"])
    }

def sequence_route_nearest_neighbor(
    truckload: Dict[str, Any], 
    distance_matrix: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Nearest-Neighbor TSP heuristic.
    Starts at home_warehouse or first order origin and routes delivery drop-offs sequentially.
    """
    orders = truckload.get("orders", [])
    if not orders:
        return {
            "sequenced_route": [],
            "total_distance_km": 0.0,
            "total_travel_time_hours": 0.0
        }
        
    # Helper to find distance
    def get_distance_and_time(o_city: str, d_city: str) -> tuple:
        for route in distance_matrix:
            if (
                (route["origin"].lower() == o_city.lower() and route["destination"].lower() == d_city.lower()) or
                (route["origin"].lower() == d_city.lower() and route["destination"].lower() == o_city.lower())
            ):
                return float(route["distance_km"]), float(route["travel_time_hours"])
        return 500.0, 6.7 # default values for safety
        
    # Start city is home_warehouse if it's not a generic ID, otherwise first order's customer_city
    start_city = truckload.get("home_warehouse", "")
    # strip "WH-" prefix to get city name if applicable
    if "wh-" in start_city.lower():
        start_city = start_city.replace("WH-", "").title()
    else:
        start_city = "Milan"  # Default hub
        
    current_city = start_city
    unvisited = [o.get("customer_city", "") for o in orders]
    # Remove duplicate customer cities (multiple orders to same city)
    unvisited = list(set(unvisited))
    
    route_sequence = [start_city]
    total_dist = 0.0
    total_time = 0.0
    
    while unvisited:
        nearest_city = ""
        min_dist = 999999.0
        min_time = 0.0
        
        for city in unvisited:
            dist, hours = get_distance_and_time(current_city, city)
            if dist < min_dist:
                min_dist = dist
                min_time = hours
                nearest_city = city
                
        total_dist += min_dist
        total_time += min_time
        route_sequence.append(nearest_city)
        current_city = nearest_city
        unvisited.remove(nearest_city)
        
    # Return round trip back to hub
    back_dist, back_time = get_distance_and_time(current_city, start_city)
    total_dist += back_dist
    total_time += back_time
    route_sequence.append(start_city)
    
    return {
        "truck_id": truckload.get("truck_id"),
        "route_sequence": route_sequence,
        "total_distance_km": round(total_dist, 1),
        "total_travel_time_hours": round(total_time, 1)
    }

def calculate_transport_kpis(
    plan: List[Dict[str, Any]], 
    trucks: List[Dict[str, Any]], 
    distance_matrix: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Calculate consolidated transit metrics (costs, emissions, travel time).
    
    Args:
        plan: List of truckloads (assignments).
        trucks: Current fleet list.
        distance_matrix: Current distance list.
    """
    total_distance = 0.0
    total_hours = 0.0
    total_cost = 0.0
    total_co2 = 0.0
    
    for truckload in plan:
        # Get sequencing details
        seq = sequence_route_nearest_neighbor(truckload, distance_matrix)
        dist = seq["total_distance_km"]
        hours = seq["total_travel_time_hours"]
        
        cost_km = float(truckload.get("cost_per_km", 1.50))
        co2_km = float(truckload.get("co2_kg_per_km", 0.82))
        
        total_distance += dist
        total_hours += hours
        total_cost += dist * cost_km
        total_co2 += dist * co2_km
        
    return {
        "total_distance_km": round(total_distance, 1),
        "total_travel_time_hours": round(total_hours, 1),
        "total_freight_cost_usd": round(total_cost, 2),
        "total_co2_emissions_kg": round(total_co2, 2)
    }
