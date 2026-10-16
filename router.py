"""
Request router.

Maps incoming requests to the appropriate status code and response body.
Unknown paths and unsupported methods return 404 for now — this will be
corrected to 405 when finding E1 is addressed.
"""


def route_request(request: dict) -> tuple[bytes, bytes]:
    """Return (status, body) for the given request dict."""
    method = request["method"]
    target = request["target"]

    if method == "GET" and target == "/":
        status = b"200 OK"
        body = b"Welcome to the home page!"

    elif method == "GET" and target == "/about":
        status = b"200 OK"
        body = b"This is the about page."

    else:
        status = b"404 Not Found"
        body = b"Not Found"

    return status, body
