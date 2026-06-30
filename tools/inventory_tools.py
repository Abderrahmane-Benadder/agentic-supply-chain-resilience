"""
Tools for inspecting warehouse stock levels and assigning orders based on distance metrics.
"""

from typing import List, Dict, Any
from tools import data_tools

def check_inventory_feasibility(
    orders: List[Dict[str, Any]], 
    warehouses: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Evaluate if warehouses have enough total and per-location inventory to cover orders.
    
    Args:
        orders: List of order dictionaries containing 'pallets' and 'order_id'.
        warehouses: List of warehouse dictionaries containing 'warehouse_id' and 'current_inventory_pallets'.
    """
    total_demand = sum(int(o.get("pallets", 0)) for o in orders)
    total_stock = sum(int(w.get("current_inventory_pallets", 0)) for w in warehouses)
    
    warehouse_details = []
    for w in warehouses:
        warehouse_details.append({
            "warehouse_id": w["warehouse_id"],
            "city": w["city"],
            "current_inventory": int(w.get("current_inventory_pallets", 0))
        })
        
    return {
        "feasible": total_stock >= total_demand,
        "total_demand_pallets": total_demand,
        "total_stock_available": total_stock,
        "global_delta_pallets": total_stock - total_demand,
        "warehouses": warehouse_details
    }

def assign_orders_to_warehouses(
    orders: List[Dict[str, Any]], 
    warehouses: List[Dict[str, Any]], 
    distance_matrix: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Assign orders to the closest warehouse that has sufficient stock available.
    
    Args:
        orders: List of order dictionaries.
        warehouses: List of warehouse dictionaries.
        distance_matrix: List of pairwise routing distance records.
    """
    # Create local mutable copy of warehouse stocks to track allocations in loop
    wh_stocks = {w["warehouse_id"]: {
        "city": w["city"], 
        "stock": int(w["current_inventory_pallets"])
    } for w in warehouses}
    
    assignments = []
    stockouts = []
    
    # Helper to find distance
    def get_distance(origin_city: str, dest_city: str) -> float:
        for route in distance_matrix:
            if (
                (route["origin"].lower() == origin_city.lower() and route["destination"].lower() == dest_city.lower()) or
                (route["origin"].lower() == dest_city.lower() and route["destination"].lower() == origin_city.lower())
            ):
                return float(route["distance_km"])
        return 9999.0 # large fallback
        
    for o in orders:
        dest_city = o.get("customer_city", "")
        pallets_needed = int(o.get("pallets", 0))
        
        # Sort warehouses by distance to customer city
        candidates = []
        for wh_id, wh_info in wh_stocks.items():
            dist = get_distance(wh_info["city"], dest_city)
            candidates.append({
                "warehouse_id": wh_id,
                "city": wh_info["city"],
                "distance": dist,
                "stock": wh_info["stock"]
            })
        candidates.sort(key=lambda x: x["distance"])
        
        assigned = False
        for cand in candidates:
            wh_id = cand["warehouse_id"]
            if wh_stocks[wh_id]["stock"] >= pallets_needed:
                # Assign to this warehouse
                wh_stocks[wh_id]["stock"] -= pallets_needed
                assignments.append({
                    "order_id": o["order_id"],
                    "customer_city": dest_city,
                    "assigned_warehouse_id": wh_id,
                    "assigned_warehouse_city": wh_stocks[wh_id]["city"],
                    "pallets": pallets_needed,
                    "distance_km": cand["distance"]
                })
                assigned = True
                break
                
        if not assigned:
            stockouts.append({
                "order_id": o["order_id"],
                "customer_city": dest_city,
                "pallets": pallets_needed,
                "reason": "Insufficient stock across all candidate warehouses"
            })
            
    return {
        "assignments": assignments,
        "stockouts": stockouts,
        "final_warehouse_stocks": {wh_id: val["stock"] for wh_id, val in wh_stocks.items()}
    }

# Standard safety stock calculation
def calculate_safety_stock(average_demand: float, lead_time_days: int, service_factor: float = 1.65) -> float:
    """Calculate safety stock limit."""
    import math
    demand_std_dev = average_demand * 0.2
    lead_time_std_dev = 1.0
    term1 = lead_time_days * (demand_std_dev ** 2)
    term2 = (average_demand ** 2) * (lead_time_std_dev ** 2)
    return service_factor * math.sqrt(term1 + term2)

def check_warehouse_inventory(warehouse_id: str) -> Dict[str, Any]:
    """Check current stock levels and capacity of a warehouse."""
    try:
        df = data_tools.load_dataset("warehouses")
        wh = df[df["warehouse_id"] == warehouse_id]
        if wh.empty:
            return {"status": "error", "message": f"Warehouse {warehouse_id} not found"}
        
        row = wh.iloc[0]
        capacity = int(row["capacity_pallets"])
        current = int(row["current_inventory_pallets"])
        return {
            "status": "success",
            "warehouse_id": warehouse_id,
            "name": row["city"],
            "city": row["city"],
            "capacity": capacity,
            "current_stock": current,
            "available_space": capacity - current,
            "utilization_pct": round((current / capacity) * 100, 2)
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

