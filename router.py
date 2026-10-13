"""
Request router.

Maps incoming requests to the appropriate status code and response body.
Unknown paths return 404. Method mismatches also return 404 for now —
this will be corrected to 405 when finding E1 is addressed.
"""


def route_request(request: dict) -> tuple[bytes, bytes]:
    """Return a (status, body) tuple for the given request.

    Args:
        request: A parsed request dictionary with at least "method" and "target".

    Returns:
        A tuple of (status_bytes, body_bytes).
    """
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
