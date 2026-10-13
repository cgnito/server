import socket

from http_parser import parse_request, read_request_body, receive_headers
from response import build_response
from router import route_request

HOST = "127.0.0.1"
PORT = 8000

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))

server_socket.listen()

print(f"Server is listening on {HOST}:{PORT}")

while True:
    connection, client_address = server_socket.accept()
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
        connection.sendall(response)

    # Execution reaches here after the `with` block closes the connection.
    # The loop goes back to accept() and waits silently for the next client.
