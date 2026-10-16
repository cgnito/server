# HTTP Server from Scratch

A basic HTTP/1.1 server built on raw Python sockets. No frameworks, no external dependencies — just the standard library.

## Purpose

This is a learning project. The goal is to understand what happens underneath common backend abstractions by implementing the pieces myself:

- TCP sockets and byte streams
- HTTP request parsing and message framing
- Request methods, targets, headers, and bodies
- HTTP response construction
- Routing and basic application behavior
- Connection lifecycle and error handling

This is not an attempt to build a production-grade server or implement every corner of the HTTP specification. The goal is a small, understandable server with clearly defined boundaries.

## Project Structure

```
server.py        # TCP socket setup, connection handling, request/response lifecycle
http_parser.py   # Request parsing: headers, request line, body framing
router.py        # Maps incoming requests to responses
response.py      # Assembles HTTP response bytes
```

## Running the Server

```bash
./scripts/start.sh
```

The server listens on `127.0.0.1:8000`.

## Testing

Run the full test suite from any working directory:

```bash
./scripts/test.sh
```

Send a request with curl:

```bash
curl http://localhost:8000/
curl http://localhost:8000/about
```

Or with a raw Python socket:

```bash
python -c "import socket; s=socket.create_connection(('127.0.0.1', 8000)); s.sendall(b'GET / HTTP/1.1\r\nHost: localhost\r\n\r\n'); print(s.recv(4096)); s.close()"
```

## Current Limitations

- Handles one connection per run, then exits
- No persistent connections
- No TLS
- No chunked transfer encoding

These are known and being addressed incrementally. See [`IMPROVEMENTS.md`](IMPROVEMENTS.md) for the full list and the planned roadmap.
