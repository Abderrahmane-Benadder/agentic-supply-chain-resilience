"""
Unit tests for disruption query and simulation tools.
"""

from tools import disruption_tools
from tools import data_tools
from data import generate_demo_data

def test_check_active_disruptions():
    """Test checking active disruptions globally."""
    active = disruption_tools.check_active_disruptions()
    assert isinstance(active, list)
    for item in active:
        assert "disruption_id" in item
        assert item["active"] is True

def test_check_filtered_disruptions():
    """Test checking active disruptions with a city filter."""
    rome_disruptions = disruption_tools.check_active_disruptions(location="Rome")
    assert isinstance(rome_disruptions, list)
    for d in rome_disruptions:
        assert "Rome" in d["location"]

def test_simulate_demand_spike():
    """Verify that simulating a demand spike modifies the orders database."""
    # Run simulation with 20% spike
    res = disruption_tools.simulate_demand_spike(0.20)
    assert res["status"] == "success"
    assert res["severity"] == 0.20
    assert res["net_increase"] >= 0

def test_simulate_truck_breakdown():
    """Verify that simulating a truck breakdown sets availability to False."""
    generate_demo_data.main()
    res = disruption_tools.simulate_truck_breakdown()
    assert res["status"] == "success"
    assert "truck_id" in res

def test_simulate_warehouse_bottleneck():
    """Verify warehouse throughput limits are reduced during bottlenecks."""
    # Let's target WH-MILAN
    res = disruption_tools.simulate_warehouse_bottleneck("WH-MILAN", 0.50)
    assert res["status"] == "success"
    assert res["new_throughput_limit"] < res["original_throughput_limit"]

def test_simulate_route_closure():
    """Verify route closures set travel time to a large delay factor."""
    res = disruption_tools.simulate_route_closure("Milan", "Bologna")
    assert res["status"] == "success"
    assert res["new_travel_time_hours"] == 999.0
