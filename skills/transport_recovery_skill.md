# Skill: Transport Recovery & Routing

- **Skill Name**: Transport Recovery Optimization
- **Purpose**: Create optimized vehicle load configurations and delivery drop-off sequences.
- **When to Use**: Invoked by the Transport Analyst after inventory allocations are verified.

## Required Inputs
* `orders` (List[Dict]): List of assigned orders.
* `trucks` (List[Dict]): Available transport fleet status.
* `distance_matrix` (List[Dict]): Routing distance matrix.

## Procedure
1. Sort orders by pallet volume in descending order.
2. Group orders into trucks using the **First-Fit Decreasing (FFD) Bin Packing Heuristic** (Max capacity: 33 pallets per truck).
3. If fleet trucks are fully allocated, dispatch spot-market **external carrier vehicles**.
4. For each truckload, solve drop-off sequencing using the **Nearest Neighbor Traveling Salesperson (TSP) Solver** starting and returning to the home hub.
5. Compute consolidated transport KPIs (mileage cost, emissions, duration).

## Expected Output
A dictionary containing:
- `truckloads`: List of grouped orders, vehicle assignments, and capacities.
- `total_distance_km`: Total transit mileage.
- `total_freight_cost_usd`: Consolidated carriage costs (incorporating external carrier markups).
- `total_co2_emissions_kg`: Combined carbon footprint.

## Failure Cases
- **No trucks available**: Both home fleet and external carrier pools are exhausted.
- **Disconnected nodes**: Destinations not linked in the distance matrix.
