import socket

from http_parser import parse_request_line

server_socket = socket.socket(
    socket.AF_INET,
    socket.SOCK_STREAM
)

server_socket.bind(("127.0.0.1", 8000))
server_socket.listen()

print("Server is listening on port 8000")
connection, client_address = server_socket.accept()

with connection:
    print(f"Connected by {client_address}")
    data = connection.recv(1024)

    request_text = data.decode("iso-8859-1")
    request_line = request_text.split("\r\n", 1)[0]

    try:
        request = parse_request_line(request_line)
    except ValueError:
        body = b"Bad Request"

        response = (
            b"HTTP/1.1 400 Bad Request\r\n"
            b"Content-Type: text/plain\r\n"
            b"Content-Length: " + str(len(body)).encode("ascii") + b"\r\n"
            b"Connection: close\r\n"
            b"\r\n"
            + body
        )

        connection.sendall(response)
    else:
        print("Method:", request["method"])
        print("Target:", request["target"])
        print("Version:", request["version"])

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
