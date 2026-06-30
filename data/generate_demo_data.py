"""
Synthetic demo data generator for the Agentic Supply Chain Resilience Platform.
Creates mock CSV datasets for orders, warehouses, trucks, suppliers, and distances in Italy.
"""

import csv
import random
from pathlib import Path

# Set seed for reproducibility
random.seed(42)

# Define file paths relative to this script
BASE_DIR = Path(__file__).resolve().parent
orders_path = BASE_DIR / "orders.csv"
warehouses_path = BASE_DIR / "warehouses.csv"
trucks_path = BASE_DIR / "trucks.csv"
suppliers_path = BASE_DIR / "suppliers.csv"
distance_matrix_path = BASE_DIR / "distance_matrix.csv"

# 1. Cities and Regions configuration
CUSTOMER_CITIES = [
    {"city": "Rome", "region": "Lazio", "lat": 41.9028, "lon": 12.4964},
    {"city": "Naples", "region": "Campania", "lat": 40.8518, "lon": 14.2681},
    {"city": "Turin", "region": "Piedmont", "lat": 45.0703, "lon": 7.6869},
    {"city": "Palermo", "region": "Sicily", "lat": 38.1157, "lon": 13.3615},
    {"city": "Genoa", "region": "Liguria", "lat": 44.4056, "lon": 8.9463},
    {"city": "Florence", "region": "Tuscany", "lat": 43.7696, "lon": 11.2558},
    {"city": "Venice", "region": "Veneto", "lat": 45.4408, "lon": 12.3155},
    {"city": "Bari", "region": "Apulia", "lat": 41.1171, "lon": 16.8719},
    {"city": "Catania", "region": "Sicily", "lat": 37.5079, "lon": 15.0830},
    {"city": "Verona", "region": "Veneto", "lat": 45.4384, "lon": 10.9916}
]

WAREHOUSE_NODES = [
    {"warehouse_id": "WH-MILAN", "city": "Milan", "capacity": 2000, "current": 1200, "throughput": 500, "lat": 45.4642, "lon": 9.1900},
    {"warehouse_id": "WH-BOLOGNA", "city": "Bologna", "capacity": 1500, "current": 800, "throughput": 400, "lat": 44.4949, "lon": 11.3426}
]

SUPPLIER_NODES = [
    {"supplier_id": "SUP-01", "city": "Turin", "reliability": 0.95, "lead_time": 3, "backup": "SUP-02", "lat": 45.0703, "lon": 7.6869},
    {"supplier_id": "SUP-02", "city": "Genoa", "reliability": 0.90, "lead_time": 4, "backup": "SUP-03", "lat": 44.4056, "lon": 8.9463},
    {"supplier_id": "SUP-03", "city": "Florence", "reliability": 0.85, "lead_time": 6, "backup": "SUP-01", "lat": 43.7696, "lon": 11.2558}
]

def generate_warehouses():
    print(f"Generating warehouses to: {warehouses_path}")
    with open(warehouses_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["warehouse_id", "city", "capacity_pallets", "current_inventory_pallets", "daily_throughput_limit"])
        for wh in WAREHOUSE_NODES:
            writer.writerow([
                wh["warehouse_id"],
                wh["city"],
                wh["capacity"],
                wh["current"],
                wh["throughput"]
            ])

def generate_suppliers():
    print(f"Generating suppliers to: {suppliers_path}")
    with open(suppliers_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["supplier_id", "city", "reliability", "lead_time_days", "backup_supplier"])
        for sup in SUPPLIER_NODES:
            writer.writerow([
                sup["supplier_id"],
                sup["city"],
                sup["reliability"],
                sup["lead_time"],
                sup["backup"]
            ])

def generate_trucks():
    print(f"Generating trucks to: {trucks_path}")
    # 6 trucks total, all standardized to 33 pallets capacity
    truck_configs = [
        {"truck_id": "TRK-01", "capacity": 33, "available": "True", "home_warehouse": "WH-MILAN", "cost": 1.50, "co2": 0.82},
        {"truck_id": "TRK-02", "capacity": 33, "available": "True", "home_warehouse": "WH-MILAN", "cost": 1.50, "co2": 0.82},
        {"truck_id": "TRK-03", "capacity": 33, "available": "True", "home_warehouse": "WH-MILAN", "cost": 1.50, "co2": 0.82},
        {"truck_id": "TRK-04", "capacity": 33, "available": "True", "home_warehouse": "WH-BOLOGNA", "cost": 1.50, "co2": 0.82},
        {"truck_id": "TRK-05", "capacity": 33, "available": "True", "home_warehouse": "WH-BOLOGNA", "cost": 1.50, "co2": 0.82},
        {"truck_id": "TRK-06", "capacity": 33, "available": "False", "home_warehouse": "WH-BOLOGNA", "cost": 1.50, "co2": 0.82}
    ]
    with open(trucks_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["truck_id", "capacity_pallets", "available", "home_warehouse", "cost_per_km", "co2_kg_per_km"])
        for trk in truck_configs:
            writer.writerow([
                trk["truck_id"],
                trk["capacity"],
                trk["available"],
                trk["home_warehouse"],
                trk["cost"],
                trk["co2"]
            ])

def generate_orders():
    print(f"Generating 40 orders to: {orders_path}")
    priorities = ["Low", "Medium", "High", "Critical"]
    families = ["Fresh", "Ambient", "Frozen"]
    
    with open(orders_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "order_id", "customer_city", "region", "pallets", 
            "due_day", "priority", "product_family", "requested_delivery_day"
        ])
        
        for i in range(1, 41):
            order_id = f"ORD-{1000 + i}"
            dest = random.choice(CUSTOMER_CITIES)
            pallets = random.randint(1, 12)
            due_day = random.randint(1, 5)
            # bias priorities slightly towards medium/high
            priority = random.choices(priorities, weights=[0.2, 0.4, 0.3, 0.1])[0]
            family = random.choice(families)
            # Requested delivery is usually 1 day before due day
            req_delivery = max(1, due_day - random.choice([0, 1]))
            
            writer.writerow([
                order_id,
                dest["city"],
                dest["region"],
                pallets,
                due_day,
                priority,
                family,
                req_delivery
            ])

def get_haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate the great-circle distance between two points in km."""
    import math
    R = 6371.0 # Earth radius in km
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def generate_distance_matrix():
    print(f"Generating distance matrix to: {distance_matrix_path}")
    
    # Compile all nodes with their coordinates
    all_locations = []
    for wh in WAREHOUSE_NODES:
        all_locations.append({"name": wh["city"], "lat": wh["lat"], "lon": wh["lon"]})
    for sup in SUPPLIER_NODES:
        all_locations.append({"name": sup["city"], "lat": sup["lat"], "lon": sup["lon"]})
    for cust in CUSTOMER_CITIES:
        all_locations.append({"name": cust["city"], "lat": cust["lat"], "lon": cust["lon"]})
        
    # De-duplicate names (e.g. Turin is both supplier and customer city, Florence is both)
    seen = set()
    unique_locations = []
    for loc in all_locations:
        if loc["name"] not in seen:
            seen.add(loc["name"])
            unique_locations.append(loc)

    with open(distance_matrix_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["origin", "destination", "distance_km", "travel_time_hours"])
        
        for loc1 in unique_locations:
            for loc2 in unique_locations:
                if loc1["name"] == loc2["name"]:
                    continue
                
                # Haversine distance
                dist = get_haversine_distance(loc1["lat"], loc1["lon"], loc2["lat"], loc2["lon"])
                
                # Adjust to driving distance (usually 1.2x to 1.3x haversine)
                driving_dist = round(dist * 1.25, 1)
                
                # Average speed of a freight truck ~75 km/h
                travel_time = round(driving_dist / 75.0, 1)
                
                writer.writerow([
                    loc1["name"],
                    loc2["name"],
                    driving_dist,
                    travel_time
                ])

def main():
    print("Starting synthetic data generation...")
    generate_warehouses()
    generate_suppliers()
    generate_trucks()
    generate_orders()
    generate_distance_matrix()
    print("Successfully generated all mock datasets for Italy supply chain demo!")

if __name__ == "__main__":
    main()
