"""
Audit logging utility to record agent compliance and safety occurrences.
"""

import json
import datetime
import uuid
from typing import Dict, Any
import config

def log_security_event(event_type: str, details: Dict[str, Any], severity: str = "INFO") -> None:
    """
    Append an entry to the audit trail log.
    """
    timestamp = datetime.datetime.now().isoformat()
    log_entry = {
        "event_id": str(uuid.uuid4())[:8],
        "timestamp": timestamp,
        "severity": severity,
        "event_type": event_type,
        "details": details
    }
    
    # Append line to log file
    try:
        with open(config.AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        print(f"Failed to write to audit log: {e}")
