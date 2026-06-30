"""
Unit tests for transport carrier search, packing algorithms, sequencing, and KPIs.
"""

from tools import transport_tools

def test_find_available_trucks():
    """Verify truck list queries work."""
    trucks = transport_tools.find_available_trucks(location="Milan")
    assert isinstance(trucks, list)

def test_calculate_route_cost_and_time():
    """Verify route cost calculations."""
    res = transport_tools.calculate_route_cost_and_time(
        source="Milan", 
        destination="Bologna", 
        weight_tons=10.0
    )
    assert res["status"] == "success"
    assert res["cost_usd"] > 0
    assert res["estimated_hours"] > 0

def test_build_truckloads_ffd():
    """Verify FFD bin packing divides orders into 33-pallet capacities."""
    orders = [
        {"order_id": "ORD-1", "pallets": 10},
        {"order_id": "ORD-2", "pallets": 12},
        {"order_id": "ORD-3", "pallets": 15},
        {"order_id": "ORD-4", "pallets": 8}
    ]
    trucks = [
        {"truck_id": "TRK-01", "capacity_pallets": 33, "available": "True", "home_warehouse": "Milan"},
        {"truck_id": "TRK-02", "capacity_pallets": 33, "available": "True", "home_warehouse": "Milan"}
    ]
    
    res = transport_tools.build_truckloads_ffd(orders, trucks)
    assert res["status"] == "success"
    assert len(res["truckloads"]) > 0
    
    # Check that no truck load exceeds capacity limit of 33 pallets
    for tl in res["truckloads"]:
        assert tl["allocated_pallets"] <= 33

def test_sequence_route_nearest_neighbor():
    """Verify nearest neighbor TSP routing returns ordered sequences."""
    truckload = {
        "truck_id": "TRK-01",
        "home_warehouse": "WH-MILAN",
        "orders": [
            {"customer_city": "Rome"},
            {"customer_city": "Bologna"}
        ]
    }
    dist_matrix = [
        {"origin": "Milan", "destination": "Bologna", "distance_km": 210.0, "travel_time_hours": 2.8},
        {"origin": "Bologna", "destination": "Rome", "distance_km": 370.0, "travel_time_hours": 4.5},
        {"origin": "Milan", "destination": "Rome", "distance_km": 570.0, "travel_time_hours": 6.8}
    ]
    
    res = transport_tools.sequence_route_nearest_neighbor(truckload, dist_matrix)
    assert "route_sequence" in res
    assert res["total_distance_km"] > 0
    # Must start and end at home warehouse
    assert res["route_sequence"][0] == "Milan"
    assert res["route_sequence"][-1] == "Milan"

def test_calculate_transport_kpis():
    """Verify routing KPI calculations compile totals."""
    plan = [
        {
            "truck_id": "TRK-01",
            "home_warehouse": "WH-MILAN",
            "cost_per_km": 1.50,
            "co2_kg_per_km": 0.82,
            "orders": [
                {"customer_city": "Rome"}
            ]
        }
    ]
    dist_matrix = [
        {"origin": "Milan", "destination": "Rome", "distance_km": 570.0, "travel_time_hours": 6.8}
    ]
    
    res = transport_tools.calculate_transport_kpis(plan, [], dist_matrix)
    assert res["total_distance_km"] > 0
    assert res["total_freight_cost_usd"] > 0
    assert res["total_co2_emissions_kg"] > 0
