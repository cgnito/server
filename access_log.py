"""
Structured access-log formatting.
"""

import json


def format_access_log(request: dict | None, status: bytes, body: bytes) -> str:
    """Return one JSON access-log line for a request and response."""
    record = {
        "method": request.get("method") if request else None,
        "target": request.get("target") if request else None,
        "version": request.get("version") if request else None,
        "status": status.decode("ascii"),
        "content_length": len(body),
    }
    return json.dumps(record, separators=(",", ":"))
