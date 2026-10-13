"""
HTTP request parser.

Responsible for reading raw bytes off a socket and turning them into a
structured request dictionary that the rest of the server can work with.

The three public functions map to three distinct phases:
  1. receive_headers  — read bytes until the header/body boundary arrives.
  2. parse_request    — decode and validate the request line and headers.
  3. read_request_body — read the body according to Content-Length.
"""


def parse_request_line(request_line: str) -> dict:
    """Parse the HTTP request line into method, target, and version.

    Raises ValueError if the line is malformed or the version is unsupported.
    """
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


def parse_request(data: bytes) -> dict:
    """Parse raw header bytes into a request dictionary.

    Expects everything up to and including the blank line (CRLFCRLF).
    Any bytes after the blank line are stored in request["body"] as a
    starting buffer for read_request_body.

    Raises ValueError on any structural problem with the request line or headers.
    """
    head, separator, body = data.partition(b"\r\n\r\n")

    if not separator:
        raise ValueError("Incomplete HTTP headers")

    lines = head.decode("iso-8859-1").split("\r\n")
    request = parse_request_line(lines[0])

    headers = {}

    for line in lines[1:]:
        if ":" not in line:
            raise ValueError("Malformed HTTP header")

        name, value = line.split(":", 1)
        name = name.strip().lower()
        value = value.strip()

        if not name:
            raise ValueError("Empty HTTP header name")

        if name in headers:
            raise ValueError("Duplicate header not supported yet")

        headers[name] = value

    request["headers"] = headers
    request["body"] = body

    return request


def receive_headers(connection) -> bytes:
    """Read from the socket until the full HTTP header section has arrived.

    Accumulates chunks in a buffer and stops as soon as the blank line
    (CRLFCRLF) that separates headers from body is found. Any bytes that
    arrived after the blank line are included in the return value and will
    be handled by read_request_body.

    Raises ConnectionError if the client disconnects before headers are complete.
    Raises ValueError if the accumulated data exceeds the size limit.
    """
    data = bytearray()
    header_end = b"\r\n\r\n"
    max_header_size = 65536

    while header_end not in data:
        chunk = connection.recv(4096)

        if not chunk:
            raise ConnectionError("Client disconnected before headers were complete")

        if len(data) + len(chunk) > max_header_size:
            raise ValueError("HTTP headers too large")

        data.extend(chunk)

    return bytes(data)


def read_request_body(connection, request: dict) -> dict:
    """Read the request body according to the Content-Length header.

    Starts from any body bytes already in request["body"] (which may have
    arrived in the same recv as the headers), then reads more from the
    socket until Content-Length bytes have been accumulated.

    Raises ConnectionError if the connection closes before the body is complete.
    """
    content_length = int(request["headers"].get("content-length", "0"))
    body = request["body"]

    while len(body) < content_length:
        chunk = connection.recv(content_length - len(body))

        if not chunk:
            raise ConnectionError("Client disconnected before body was complete")

        body += chunk

    request["body"] = body
    return request
