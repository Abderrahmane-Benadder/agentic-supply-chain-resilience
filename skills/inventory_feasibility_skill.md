# Skill: Inventory Feasibility Check

- **Skill Name**: Inventory Reallocation Feasibility
- **Purpose**: Verify if warehouses have sufficient inventory capacity to handle disrupted order redirections.
- **When to Use**: Invoked after affected orders are filtered by the Demand Analyst.

## Required Inputs
* `orders` (List[Dict]): List of impacted customer orders.
* `warehouses` (List[Dict]): Current warehouses inventory status.
* `distance_matrix` (List[Dict]): Pairwise route mapping metrics.

## Procedure
1. Verify if total capacity across candidate hubs is greater than or equal to total order pallets demand.
2. Sort alternate warehouses by driving distance relative to each order's customer city.
3. Map orders to the closest available warehouse that contains sufficient inventory.
4. Deduct allocated pallets from warehouses.
5. If no candidate warehouse has sufficient stock, flag the order as a **Stockout**.

## Expected Output
A dictionary containing:
- `assignments`: List of successfully routed orders with target warehouses and distance in km.
- `stockouts`: List of orders unable to be fulfilled due to capacity deficits.
- `final_warehouse_stocks`: Remaining stock balances per warehouse ID.

## Failure Cases
- **Complete Stockout**: Total demand exceeds total available stock. Flag as unfeasible.
- **Invalid Warehouse ID**: Warehouse target not found in baseline registry.
