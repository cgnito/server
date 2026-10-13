def parse_request_line(request_line: str) -> dict:
    parts = request_line.split(" ")

    if len(parts) != 3 or not all(parts):
        raise ValueError("Malformed HTTP request line")

    method, target, version = parts

    if not method.isascii() or not method.isalpha():
        raise ValueError("Invalid HTTP method")

    if not target:
        raise ValueError("Missing request target")

    if version not in ("HTTP/1.0", "HTTP/1.1"):
        raise ValueError("Unsupported HTTP version")

    return {
        "method": method,
        "target": target,
        "version": version,
    }
