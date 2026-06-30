"""
Unit tests for data loading, fetching, and validation tools.
"""

import pytest
from tools import data_tools

def test_load_functions():
    """Verify all individual load functions return lists of dictionaries."""
    orders = data_tools.load_orders()
    assert isinstance(orders, list)
    if orders:
        assert isinstance(orders[0], dict)
        assert "order_id" in orders[0]

    warehouses = data_tools.load_warehouses()
    assert isinstance(warehouses, list)
    if warehouses:
        assert "warehouse_id" in warehouses[0]

    trucks = data_tools.load_trucks()
    assert isinstance(trucks, list)
    if trucks:
        assert "truck_id" in trucks[0]

    suppliers = data_tools.load_suppliers()
    assert isinstance(suppliers, list)
    if suppliers:
        assert "supplier_id" in suppliers[0]

    dist = data_tools.load_distance_matrix()
    assert isinstance(dist, list)
    if dist:
        assert "origin" in dist[0]

def test_validate_datasets():
    """Verify validate_dataset checks columns and validates datasets successfully."""
    # Test valid dataset
    res = data_tools.validate_dataset("orders")
    assert res["valid"] is True
    assert len(res["errors"]) == 0

    # Test unknown dataset
    res_unknown = data_tools.validate_dataset("invalid_dataset_name")
    assert res_unknown["valid"] is False
    assert "Unknown dataset name" in res_unknown["errors"][0]

def test_get_order_by_id():
    """Verify fetching an order by ID works."""
    orders = data_tools.load_orders()
    if orders:
        target_id = orders[0]["order_id"]
        order = data_tools.get_order_by_id(target_id)
        assert order is not None
        assert order["order_id"] == target_id

    # Non-existent order
    assert data_tools.get_order_by_id("ORD-NONEXISTENT") is None
