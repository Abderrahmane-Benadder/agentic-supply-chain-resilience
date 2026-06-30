# Skill: Plan Evaluation & Scorecarding

- **Skill Name**: Scorecarding and Plan Evaluation
- **Purpose**: Calculate baseline, disrupted, and recovery state KPIs to evaluate mitigation effectiveness.
- **When to Use**: Triggered at the end of the simulation pipeline to evaluate alternative routing plans.

## Required Inputs
* `baseline_kpis` (Dict): Baseline KPIs.
* `disrupted_kpis` (Dict): Disrupted KPIs.
* `recovery_kpis` (Dict): Recovery KPIs.

## Procedure
1. Verify inputs are complete (Freight cost, Service OTIF, carbon emissions, delay hours).
2. Calculate cost variances and OTIF service recoveries.
3. Formulate comparison metrics table.
4. Determine feasibility status based on budget rules (max $50,000) and resilience scores.

## Expected Output
A scorecard dictionary containing:
- `comparison_table`: Metric arrays for Baseline, Disrupted, and Recovery states.
- `cost_variance_usd`: Carriage cost difference.
- `service_level_recovery_pct`: Service level improvement (OTIF delta).
- `status`: Feasible or High Risk classification.

## Failure Cases
- **Missing Baseline metrics**: Compare is impossible without initial reference markers.
- **Divison by zero**: Empty plan yields invalid metrics.
