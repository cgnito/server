"""
HTTP request parser.

Converts raw bytes into a structured request dict through three steps:
receive_headers, parse_request, then read_request_body.
"""


def parse_request_line(request_line: str) -> dict:
    """Parse the HTTP request line into method, target, and version.

    Raises ValueError if the line is malformed or the version is unsupported.
    """
    parts = request_line.split(" ")

    if len(parts) != 3 or not all(parts):
        raise ValueError("Malformed HTTP request line")

    method, target, version = parts

    if not method.isascii() or not method.isalpha() or not method.isupper():
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


# Duplicate Content-Length is a known request-smuggling vector;
# Host must appear exactly once in HTTP/1.1 (RFC 7230 §5.4).
SINGULAR_HEADERS = frozenset({"content-length", "host"})
MAX_BODY_SIZE = 1024 * 1024


class RequestBodyTooLarge(ValueError):
    """Raised when Content-Length exceeds the maximum request body size."""


class UnsupportedTransferEncoding(ValueError):
    """Raised when a request uses unsupported transfer encoding."""


def parse_request(data: bytes) -> dict:
    """Parse raw bytes (headers + initial body chunk) into a request dictionary.

    Raises ValueError on any structural problem with the request or headers.
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
            if name in SINGULAR_HEADERS:
                raise ValueError(f"Duplicate {name!r} header is not allowed")
            # RFC 7230 §3.2.2: combine repeated field values with ", "
            headers[name] = headers[name] + ", " + value
        else:
            headers[name] = value

    if "transfer-encoding" in headers:
        raise UnsupportedTransferEncoding("Transfer-Encoding is not supported")

    if request["version"] == "HTTP/1.1" and "host" not in headers:
        raise ValueError("HTTP/1.1 requests must include a Host header")

    request["headers"] = headers
    request["body"] = body

    return request


def receive_headers(connection) -> bytes:
    """Read from the socket until \\r\\n\\r\\n arrives, then return all bytes received.

    Raises ConnectionError if the client disconnects early.
    Raises ValueError if headers exceed the size limit.
    """
    data = bytearray()
    header_end = b"\r\n\r\n"
    max_header_size = 65536

    while header_end not in data:
        chunk = connection.recv(4096)

        if not chunk:
            raise ConnectionError("Client disconnected before headers were complete")

        data.extend(chunk)

        # Only raise if the terminator still hasn't arrived — a valid request
        # whose final chunk pushes past the limit must not be rejected.
        if header_end not in data and len(data) > max_header_size:
            raise ValueError("HTTP headers too large")

    return bytes(data)


def read_request_body(connection, request: dict) -> dict:
    """Read exactly Content-Length bytes for the request body.

    Raises ConnectionError if the connection closes before the body is complete.
    """
    if "content-length" not in request["headers"]:
        request["body"] = b""
        return request

    raw_content_length = request["headers"].get("content-length", "0")

    try:
        content_length = int(raw_content_length)
    except ValueError:
        raise ValueError("Content-Length is not an integer")

    if content_length < 0:
        raise ValueError("Content-Length must not be negative")

    if content_length > MAX_BODY_SIZE:
        raise RequestBodyTooLarge("Request body too large")

    body = request["body"]

    while len(body) < content_length:
        chunk = connection.recv(content_length - len(body))

        if not chunk:
            raise ConnectionError("Client disconnected before body was complete")

        body += chunk

    request["body"] = body
    return request
