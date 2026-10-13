import socket

from http_parser import parse_request, receive_headers, read_request_body

server_socket = socket.socket(
    socket.AF_INET,
    socket.SOCK_STREAM
)

HOST = "127.0.0.1"
PORT = 8000
server_socket.bind((HOST, PORT))
server_socket.listen()

print(f"Server is listening on port {PORT}")
connection, client_address = server_socket.accept()

with connection:
    print(f"Connected by {client_address}")
    try:
        data = receive_headers(connection)
        request = parse_request(data)
        request = read_request_body(connection, request)


        print("Method:", request["method"])
        print("Target:", request["target"])
        print("Version:", request["version"])
        print("Headers:", request["headers"])
        print("Body:", request["body"])

    except (ValueError, ConnectionError) as error:
        print("Request error:", error)

        #fixxxxxxxxxxxxx
        # Continue with normal request handling here.

    if request["method"] == "GET" and request["target"] == "/":
        status = b"200 OK"
        body = b"Welcome to the home page!"

    elif request["method"] == "GET" and request["target"] == "/about":
        status = b"200 OK"
        body = b"This is the about page."

    else:
        status = b"404 Not Found"
        body = b"Not Found"

    response = (
        b"HTTP/1.1 " + status + b"\r\n"
        b"Content-Type: text/plain\r\n"
        b"Content-Length: " + str(len(body)).encode("ascii") + b"\r\n"
        b"Connection: close\r\n"
        b"\r\n"
        + body
    )

    connection.sendall(response)
server_socket.close()



# to test: python3 -c "import socket; s=socket.create_connection(('127.0.0.1', 8000)); s.sendall(b'Hello server'); print(s.recv(1024)); s.close()"
