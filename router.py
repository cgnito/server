"""
Request router.

Maps incoming requests to the appropriate status code and response body.
Unknown paths and unsupported methods return 404 for now — this will be
corrected to 405 when finding E1 is addressed.
"""


def route_request(request: dict) -> tuple[bytes, bytes, bytes, dict[bytes, bytes]]:
    """Return (status, body, content_type, headers) for a request."""
    method = request["method"]
    target = request["target"]

    if method == "GET" and target == "/":
        status = b"200 OK"
        body = b"Welcome to the home page!"
        content_type = b"text/plain"
        headers = {}

    elif method == "GET" and target == "/about":
        status = b"200 OK"
        body = b"This is the about page."
        content_type = b"text/plain"
        headers = {}

    elif method == "GET" and target == "/json":
        status = b"200 OK"
        body = b'{"message": "Hello from JSON"}'
        content_type = b"application/json"
        headers = {}

    elif method == "GET" and target == "/html":
        status = b"200 OK"
        body = b"<h1>Hello from HTML</h1>"
        content_type = b"text/html"
        headers = {}

    elif target in ("/", "/about", "/json", "/html"):
        status = b"405 Method Not Allowed"
        body = b"Method Not Allowed"
        content_type = b"text/plain"
        headers = {b"Allow": b"GET"}

    else:
        status = b"404 Not Found"
        body = b"Not Found"
        content_type = b"text/plain"
        headers = {}

    return status, body, content_type, headers
