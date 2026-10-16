"""
HTTP response builder.

Assembles a raw HTTP/1.1 response byte string from a status code and body.
"""


def build_response(
    status: bytes,
    body: bytes,
    content_type: bytes = b"text/plain",
) -> bytes:
    """Assemble a complete HTTP/1.1 response from status bytes and body bytes."""
    response = (
        b"HTTP/1.1 " + status + b"\r\n"
        b"Content-Type: " + content_type + b"\r\n"
        b"Content-Length: " + str(len(body)).encode("ascii") + b"\r\n"
        b"Connection: close\r\n"
        b"\r\n"
        + body
    )

    return response
