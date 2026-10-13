def route_request(request):
    method = request["method"]
    target = request["target"]

    if method == "GET" and target == "/":
        status = b"200 OK"
        body = b"Welcome to the home page!"

    elif method == "GET" and target == "/about":
        status = b"200 OK"
        body = b"This is the about page."

    else:
        status = b"404 Not Found"
        body = b"Not Found"

    return status, body
