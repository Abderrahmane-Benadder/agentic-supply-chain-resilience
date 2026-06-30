"""
Tools for loading, saving, and validating supply chain CSV datasets.
"""

import os
import json
import pandas as pd
from typing import Dict, Any, List, Optional
import config

def load_dataset(name: str) -> pd.DataFrame:
    """
    Load a dataset from the CSV directory.
    
    Args:
        name: Name of the CSV file without extension (e.g., 'orders').
    """
    path = config.DATA_DIR / f"{name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Dataset {name} not found at {path}")
    return pd.read_csv(path)

def save_dataset(name: str, df: pd.DataFrame) -> None:
    """
    Save a DataFrame back to the CSV directory.
    
    Args:
        name: Name of the CSV file without extension.
        df: Pandas DataFrame to persist.
    """
    path = config.DATA_DIR / f"{name}.csv"
    df.to_csv(path, index=False)

def load_orders() -> List[Dict[str, Any]]:
    """Load and return all orders as a list of dictionaries."""
    try:
        df = load_dataset("orders")
        return df.to_dict(orient="records")
    except Exception as e:
        print(f"Error loading orders: {e}")
        return []

def load_warehouses() -> List[Dict[str, Any]]:
    """Load and return all warehouses as a list of dictionaries."""
    try:
        df = load_dataset("warehouses")
        return df.to_dict(orient="records")
    except Exception as e:
        print(f"Error loading warehouses: {e}")
        return []

def load_trucks() -> List[Dict[str, Any]]:
    """Load and return all trucks as a list of dictionaries."""
    try:
        df = load_dataset("trucks")
        return df.to_dict(orient="records")
    except Exception as e:
        print(f"Error loading trucks: {e}")
        return []

def load_suppliers() -> List[Dict[str, Any]]:
    """Load and return all suppliers as a list of dictionaries."""
    try:
        df = load_dataset("suppliers")
        return df.to_dict(orient="records")
    except Exception as e:
        print(f"Error loading suppliers: {e}")
        return []

def load_distance_matrix() -> List[Dict[str, Any]]:
    """Load and return the distance matrix as a list of dictionaries."""
    try:
        df = load_dataset("distance_matrix")
        return df.to_dict(orient="records")
    except Exception as e:
        print(f"Error loading distance matrix: {e}")
        return []

def validate_dataset(name: str) -> Dict[str, Any]:
    """
    Validate a dataset by checking columns and null values.
    
    Args:
        name: Name of the CSV file.
    
    Returns:
        Dictionary with validation results: {"valid": bool, "errors": List[str]}
    """
    expected_cols = {
        "orders": [
            "order_id", "customer_city", "region", "pallets", 
            "due_day", "priority", "product_family", "requested_delivery_day"
        ],
        "warehouses": [
            "warehouse_id", "city", "capacity_pallets", 
            "current_inventory_pallets", "daily_throughput_limit"
        ],
        "trucks": [
            "truck_id", "capacity_pallets", "available", 
            "home_warehouse", "cost_per_km", "co2_kg_per_km"
        ],
        "suppliers": [
            "supplier_id", "city", "reliability", "lead_time_days", "backup_supplier"
        ],
        "distance_matrix": [
            "origin", "destination", "distance_km", "travel_time_hours"
        ]
    }
    
    errors = []
    if name not in expected_cols:
        return {"valid": False, "errors": [f"Unknown dataset name: {name}"]}
        
    try:
        df = load_dataset(name)
        # Check columns
        for col in expected_cols[name]:
            if col not in df.columns:
                errors.append(f"Missing column: {col}")
                
        # Check null values
        null_counts = df.isnull().sum()
        for col, count in null_counts.items():
            if count > 0:
                errors.append(f"Column '{col}' has {count} null values")
    except Exception as e:
        errors.append(f"Failed to load dataset: {str(e)}")
        
    return {
        "valid": len(errors) == 0,
        "errors": errors
    }

def get_order_by_id(order_id: str) -> Optional[Dict[str, Any]]:
    """Fetch details of a single order by its ID."""
    try:
        df = load_dataset("orders")
        record = df[df["order_id"] == order_id]
        if record.empty:
            return None
        return record.iloc[0].to_dict()
    except Exception:
        return None

def load_planner_preferences() -> Dict[str, Any]:
    """Load user preferences from JSON memory."""
    path = os.path.join(config.BASE_DIR, "memory", "planner_preferences.json")
    if not os.path.exists(path):
        return {
            "min_truck_utilization": 0.85,
            "max_delay_days": 1,
            "cost_priority": "high",
            "co2_priority": "medium",
            "service_level_target": 0.95,
            "human_approval_required_if_cost_increase_above": 0.15
        }
    with open(path, "r") as f:
        return json.load(f)

def update_planner_preferences(new_prefs: Dict[str, Any]) -> bool:
    """Overwrite user preferences in JSON memory."""
    try:
        path = os.path.join(config.BASE_DIR, "memory", "planner_preferences.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(new_prefs, f, indent=2)
        return True
    except Exception:
        return False

def load_session_state() -> Dict[str, Any]:
    """Load persistent session state tracking data."""
    path = os.path.join(config.BASE_DIR, "memory", "session_state.json")
    if not os.path.exists(path):
        return {
            "selected_scenario": "",
            "severity": "",
            "baseline_kpis": {},
            "disrupted_kpis": {},
            "recovery_kpis": {},
            "agent_trace": [],
            "final_decision": ""
        }
    with open(path, "r") as f:
        return json.load(f)

def save_session_state(state: Dict[str, Any]) -> bool:
    """Save session state tracking variables to JSON memory."""
    try:
        path = os.path.join(config.BASE_DIR, "memory", "session_state.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(state, f, indent=2)
        return True
    except Exception:
        return False

