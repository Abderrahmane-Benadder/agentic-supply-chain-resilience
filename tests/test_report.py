"""
Unit tests for reporting and trace logging tools.
"""

from tools import report_tools

def test_generate_manager_summary():
    """Verify that manager brief generates expected summary text."""
    results = {
        "session_id": "test_id_123",
        "scenario": "Rome Station Outage",
        "evaluation": {
            "total_recovery_cost_usd": 1500.00,
            "resilience_score": 75.0
        }
    }
    res = report_tools.generate_manager_summary(results)
    assert res["status"] == "success"
    assert "test_id_123" in res["summary"]
    assert res["resilience_score"] == 75.0
    assert res["cost"] == 1500.00

def test_export_trace_json():
    """Verify trace saving wraps successfully."""
    trace = {
        "session_id": "test_trace_123",
        "steps": [{"step": "Init", "status": "Passed"}]
    }
    res = report_tools.export_trace_json(trace)
    assert res["status"] == "success"
    assert "file_path" in res

def test_export_report_markdown():
    """Verify markdown report generation wraps successfully."""
    results = {
        "session_id": "test_report_123",
        "scenario": "Rome Outage",
        "disruptions": [{"type": "Weather", "location": "Rome", "description": "Rain", "severity": "High"}],
        "evaluation": {
            "total_cost_usd": 1200.00,
            "total_delay_hours": 4.0,
            "resilience_score": 62.0
        },
        "explanation": "Test explanation rationale."
    }
    res = report_tools.export_report_markdown(results)
    assert res["status"] == "success"
    assert "file_path" in res
