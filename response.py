"""
HTTP response builder.

Assembles a raw HTTP/1.1 response byte string from a status code and body.
"""


def build_response(status: bytes, body: bytes) -> bytes:
    """Build a complete HTTP/1.1 response ready to send over a socket.

    Args:
        status: The status code and reason phrase, e.g. b"200 OK".
        body:   The response body as bytes.

    Returns:
        The full response including status line, headers, blank line, and body.
    """
    response = (
        b"HTTP/1.1 " + status + b"\r\n"
        b"Content-Type: text/plain\r\n"
        b"Content-Length: " + str(len(body)).encode("ascii") + b"\r\n"
        b"Connection: close\r\n"
        b"\r\n"
        + body
    )

    return response
