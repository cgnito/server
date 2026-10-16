"""
HTTP server entry point.

Creates the TCP socket, binds to a port, and runs the accept loop.
"""

import os
import socket

from http_parser import parse_request, read_request_body, receive_headers
from response import build_response
from router import route_request

HOST = "127.0.0.1"
PORT = 8000

# How long to wait for a client to finish sending its request.
CONNECTION_TIMEOUT = int(os.environ.get("CONNECTION_TIMEOUT", "30"))

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Prevents "Address already in use" on quick restart (TCP TIME_WAIT).
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

server_socket.bind((HOST, PORT))
server_socket.listen()

print(f"Server is listening on {HOST}:{PORT}")

try:
    while True:
        connection, client_address = server_socket.accept()
        connection.settimeout(CONNECTION_TIMEOUT)
        print(f"Connection from {client_address}")

        with connection:
            try:
                data = receive_headers(connection)
                request = parse_request(data)
                request = read_request_body(connection, request)

                status, body = route_request(request)

                print(f"  method:  {request['method']}")
                print(f"  target:  {request['target']}")
                print(f"  version: {request['version']}")
                print(f"  headers: {request['headers']}")
                print(f"  body:    {request['body']}")

            except socket.timeout:
                print(f"  [!] request timed out ({CONNECTION_TIMEOUT}s)")
                status = b"408 Request Timeout"
                body = b"Request Timeout"

            except ValueError as error:
                print(f"  [!] request error: {error}")
                status = b"400 Bad Request"
                body = b"Bad Request"

            except ConnectionError as error:
                print(f"  [!] connection error: {error}")
                status = b"400 Bad Request"
                body = b"Incomplete Request"

            except Exception as error:
                print(f"  [!] unexpected error: {error}")
                status = b"500 Internal Server Error"
                body = b"Internal Server Error"

            response = build_response(status, body)

            try:
                connection.sendall(response)
            except OSError as error:
                print(f"  [!] failed to send response: {error}")

except KeyboardInterrupt:
    print("\nServer stopped.")
finally:
    server_socket.close()
