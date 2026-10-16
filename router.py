"""
Request router.

Maps request paths and methods to response handlers.
"""


def home_page(request: dict) -> tuple[bytes, bytes, bytes, dict[bytes, bytes]]:
    """Return the home page response."""
    return b"200 OK", b"Welcome to the home page!", b"text/plain", {}


def about_page(request: dict) -> tuple[bytes, bytes, bytes, dict[bytes, bytes]]:
    """Return the about page response."""
    return b"200 OK", b"This is the about page.", b"text/plain", {}


def json_page(request: dict) -> tuple[bytes, bytes, bytes, dict[bytes, bytes]]:
    """Return a JSON response."""
    return b"200 OK", b'{"message": "Hello from JSON"}', b"application/json", {}


def html_page(request: dict) -> tuple[bytes, bytes, bytes, dict[bytes, bytes]]:
    """Return an HTML response."""
    return b"200 OK", b"<h1>Hello from HTML</h1>", b"text/html", {}


ROUTES = {
    "/": {"GET": home_page},
    "/about": {"GET": about_page},
    "/json": {"GET": json_page},
    "/html": {"GET": html_page},
}


def route_request(request: dict) -> tuple[bytes, bytes, bytes, dict[bytes, bytes]]:
    """Look up a path and method, then return its response details."""
    method = request["method"]
    target = request["target"]
    path_routes = ROUTES.get(target)

    if path_routes is None:
        return b"404 Not Found", b"Not Found", b"text/plain", {}

    handler = path_routes.get(method)

    if handler is None:
        allowed_methods = ", ".join(path_routes).encode("ascii")
        return (
            b"405 Method Not Allowed",
            b"Method Not Allowed",
            b"text/plain",
            {b"Allow": allowed_methods},
        )

    return handler(request)
