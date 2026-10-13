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



def parse_request(data: bytes) -> dict:
    # Separate the headers from any bytes after them.
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


def receive_headers(connection):
    data = bytearray()
    header_end = b"\r\n\r\n"
    max_header_size = 65536

    while header_end not in data:
        chunk = connection.recv(4096)

        if not chunk:
            raise ConnectionError("Client disconnected")

        data.extend(chunk)

        if len(data) > max_header_size:
            raise ValueError("HTTP headers too large")

    return bytes(data)



def read_request_body(connection, request):
    content_length = int(request["headers"].get("content-length", "0"))
    body = request["body"]

    while len(body) < content_length:
        chunk = connection.recv(content_length - len(body))

        if not chunk:
            raise ConnectionError("Incomplete request body")

        body += chunk

    request["body"] = body
    return request
