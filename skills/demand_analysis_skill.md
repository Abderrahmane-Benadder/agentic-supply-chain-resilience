# Skill: Demand Analysis

- **Skill Name**: Demand Impact Analysis
- **Purpose**: Identify customer orders, regions, and deadlines affected by a logistics disruption.
- **When to Use**: Triggered immediately after a weather hazard, strike, or network closure is identified.

## Required Inputs
* `location` (string): Affected city location (e.g. Rome, Naples).
* `orders_list` (List[Dict]): List of customer orders.

## Procedure
1. Scan the list of active customer orders.
2. Filter for orders whose `customer_city` matches the disrupted `location`.
3. Check the `priority` profile (Critical > High > Medium > Low).
4. Check the `due_day` to assess SLA urgency boundaries.
5. Compile and output a list of impacted orders.

## Expected Output
A JSON list of affected orders containing:
- `order_id`
- `customer_city`
- `pallets`
- `due_day`
- `priority`

## Failure Cases
- **No orders found**: No active deliveries are scheduled for the location. Return an empty list.
- **Missing schema columns**: Raise a data validation error.
