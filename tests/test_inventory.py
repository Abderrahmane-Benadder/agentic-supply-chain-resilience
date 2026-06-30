"""
Unit tests for warehouse inventory checks and orders assignment heuristics.
"""

from tools import inventory_tools

def test_check_inventory_feasibility():
    """Verify inventory feasibility assessment metrics."""
    orders = [{"order_id": "ORD-1", "pallets": 10}, {"order_id": "ORD-2", "pallets": 20}]
    warehouses = [
        {"warehouse_id": "WH-MILAN", "city": "Milan", "current_inventory_pallets": 25},
        {"warehouse_id": "WH-BOLOGNA", "city": "Bologna", "current_inventory_pallets": 10}
    ]
    
    # total demand: 30. total stock: 35. -> feasible
    res = inventory_tools.check_inventory_feasibility(orders, warehouses)
    assert res["feasible"] is True
    assert res["total_demand_pallets"] == 30
    assert res["total_stock_available"] == 35
    assert res["global_delta_pallets"] == 5

    # total demand: 40. total stock: 35. -> unfeasible
    orders.append({"order_id": "ORD-3", "pallets": 10})
    res = inventory_tools.check_inventory_feasibility(orders, warehouses)
    assert res["feasible"] is False

def test_assign_orders_to_warehouses():
    """Verify that nearest warehouse allocations avoid capacity stockouts."""
    orders = [
        {"order_id": "ORD-1", "customer_city": "Rome", "pallets": 5},
        {"order_id": "ORD-2", "customer_city": "Naples", "pallets": 10}
    ]
    warehouses = [
        {"warehouse_id": "WH-MILAN", "city": "Milan", "current_inventory_pallets": 20},
        {"warehouse_id": "WH-BOLOGNA", "city": "Bologna", "current_inventory_pallets": 3}
    ]
    dist_matrix = [
        {"origin": "Milan", "destination": "Rome", "distance_km": 570.0, "travel_time_hours": 6.8},
        {"origin": "Milan", "destination": "Naples", "distance_km": 750.0, "travel_time_hours": 9.0},
        {"origin": "Bologna", "destination": "Rome", "distance_km": 380.0, "travel_time_hours": 4.5},
        {"origin": "Bologna", "destination": "Naples", "distance_km": 560.0, "travel_time_hours": 6.5}
    ]
    
    res = inventory_tools.assign_orders_to_warehouses(orders, warehouses, dist_matrix)
    assert "assignments" in res
    assert "stockouts" in res
    
    # ORD-1 requires 5 pallets. WH-Bologna only has 3. So it must get assigned to WH-Milan.
    # Check that assignment was routed to WH-MILAN
    mil_assigned = [a for a in res["assignments"] if a["order_id"] == "ORD-1"]
    assert len(mil_assigned) == 1
    assert mil_assigned[0]["assigned_warehouse_id"] == "WH-MILAN"
