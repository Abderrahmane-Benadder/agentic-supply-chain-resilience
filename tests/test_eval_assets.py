"""
Tests for ADK/agents-cli evaluation assets.
"""

import json
from pathlib import Path


def test_basic_eval_dataset_has_cases():
    path = Path("tests/eval/datasets/basic-dataset.json")
    data = json.loads(path.read_text())

    cases = data["eval_cases"]
    assert len(cases) >= 3
    assert all(case.get("eval_case_id") for case in cases)
    assert all(case.get("prompt", {}).get("role") == "user" for case in cases)


def test_eval_config_declares_quality_safety_and_boundary_checks():
    text = Path("tests/eval/eval_config.yaml").read_text()

    assert "final_response_quality" in text
    assert "safety" in text
    assert "calculation_boundary_grounding" in text
