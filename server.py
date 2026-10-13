import socket

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

    request_text = data.decode("utf-8")
    request_line = request_text.split("\r\n")[0]

    method, path, version = request_line.split(" ")

    print("Method:", method)
    print("Path:", path)
    print("Version:", version)

    if method == "GET" and path == "/":
        body = b"Welcome to the home page!"

    elif method == "GET" and path == "/about":
        body = b"This is the about page."

    else:
        body = b"Not Found"

    print(f"Received: {data!r}")

    response = (
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Type: text/plain\r\n"
        b"Content-Length: " + str(len(body)).encode("ascii") + b"\r\n"
        b"Connection: close\r\n"
        b"\r\n"
        + body
    )

    connection.sendall(response)
server_socket.close()



# to test: python3 -c "import socket; s=socket.create_connection(('127.0.0.1', 8000)); s.sendall(b'Hello server'); print(s.recv(1024)); s.close()"
