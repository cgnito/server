"""
Integration tests for server.py.

These tests start the server as a real subprocess and communicate with it
over a TCP socket. They verify the full request/response cycle and the
connection-handling behaviour that cannot be tested with unit tests alone
(because it involves a live socket, a running process, and real I/O).
"""

import os
import signal
import socket
import struct
import subprocess
import time
import unittest

HOST = "127.0.0.1"
PORT = 8000

# Absolute path to the server/ directory so subprocess can find server.py
# regardless of where the test runner is invoked from.
SERVER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def send_request(raw: bytes, timeout: float = 2.0) -> bytes:
    """Open a connection, send raw bytes, return the full response."""
    s = socket.create_connection((HOST, PORT), timeout=timeout)
    s.sendall(raw)
    response = s.recv(4096)
    s.close()
    return response


class TestServerIntegration(unittest.TestCase):

    def setUp(self):
        """Start the server subprocess before each test.

        CONNECTION_TIMEOUT is set to 1 second so that timeout-related tests
        complete quickly. The real default (30 s) is only used in production.
        """
        self.process = subprocess.Popen(
            ["python3", "server.py"],
            cwd=SERVER_DIR,
            env={**os.environ, "CONNECTION_TIMEOUT": "1"},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._wait_for_server()

    def tearDown(self):
        """Terminate the server subprocess after each test.

        poll() returns None if the process is still running, or its exit code
        if it already exited (e.g. the test sent SIGINT). We skip terminate()
        in the latter case to avoid sending a signal to a dead process.
        """
        if self.process.poll() is None:
            self.process.terminate()
        self.process.wait()

    def _wait_for_server(self, attempts: int = 20, delay: float = 0.05):
        """Poll until the server is accepting connections, or fail."""
        for _ in range(attempts):
            try:
                s = socket.create_connection((HOST, PORT), timeout=0.2)
                s.close()
                return
            except (ConnectionRefusedError, socket.timeout):
                time.sleep(delay)
        self.fail("Server did not start in time")

    # ── Basic correctness ──────────────────────────────────────────────────

    def test_get_root_returns_200(self):
        response = send_request(b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n")
        self.assertIn(b"200 OK", response)

    def test_get_about_returns_200(self):
        response = send_request(b"GET /about HTTP/1.1\r\nHost: localhost\r\n\r\n")
        self.assertIn(b"200 OK", response)

    def test_get_json_returns_json_content_type(self):
        response = send_request(b"GET /json HTTP/1.1\r\nHost: localhost\r\n\r\n")
        self.assertIn(b"200 OK", response)
        self.assertIn(b"Content-Type: application/json\r\n", response)

    def test_get_html_returns_html_content_type(self):
        response = send_request(b"GET /html HTTP/1.1\r\nHost: localhost\r\n\r\n")
        self.assertIn(b"200 OK", response)
        self.assertIn(b"Content-Type: text/html\r\n", response)

    def test_unknown_path_returns_404(self):
        response = send_request(b"GET /nope HTTP/1.1\r\nHost: localhost\r\n\r\n")
        self.assertIn(b"404", response)

    def test_malformed_request_returns_400(self):
        response = send_request(b"THIS IS NOT HTTP\r\n\r\n")
        self.assertIn(b"400", response)

    def test_oversized_request_body_returns_413(self):
        request = (
            b"POST / HTTP/1.1\r\n"
            b"Host: localhost\r\n"
            b"Content-Length: 1048577\r\n"
            b"\r\n"
        )
        response = send_request(request)
        self.assertIn(b"413", response)

    def test_transfer_encoding_returns_501(self):
        request = (
            b"POST / HTTP/1.1\r\n"
            b"Host: localhost\r\n"
            b"Transfer-Encoding: chunked\r\n"
            b"\r\n"
        )
        response = send_request(request)
        self.assertIn(b"501", response)

    def test_http11_without_host_returns_400(self):
        # HTTP/1.1 requires a Host header. Missing one must return 400.
        response = send_request(b"GET / HTTP/1.1\r\n\r\n")
        self.assertIn(b"400", response)

    # ── Connection handling ────────────────────────────────────────────────

    def test_handles_multiple_sequential_requests(self):
        """The server must still be alive and responsive after the first connection closes."""
        r1 = send_request(b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n")
        r2 = send_request(b"GET /about HTTP/1.1\r\nHost: localhost\r\n\r\n")
        self.assertIn(b"200 OK", r1)
        self.assertIn(b"200 OK", r2)

    def test_survives_abrupt_disconnect(self):
        """Server keeps running after a client closes without reading the response.

        We force an RST (reset) instead of a normal FIN by setting SO_LINGER
        with a zero timeout. An RST tears the connection down immediately and
        causes the server's sendall() to raise ConnectionResetError — the
        exact error that finding A3 guards against.

        After the abrupt close, the server must still accept and answer the
        next request normally.
        """
        s = socket.create_connection((HOST, PORT), timeout=2)
        s.sendall(b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n")

        # SO_LINGER with l_onoff=1, l_linger=0 makes close() send RST
        # rather than FIN, so the server gets a hard reset mid-response.
        s.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
        s.close()

        time.sleep(0.1)  # Give the server a moment to process the error.

        # The server must still be responsive after the broken connection.
        response = send_request(b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n")
        self.assertIn(b"200 OK", response)


    # ── Shutdown behaviour ─────────────────────────────────────────────────

    def test_clean_shutdown_on_sigint(self):
        """Server exits with code 0 when sent SIGINT (the Ctrl-C signal).

        Without a try/finally, KeyboardInterrupt propagates unhandled and
        Python exits with code 1. With the handler in place the server closes
        its socket and exits cleanly with code 0.
        """
        self.process.send_signal(signal.SIGINT)
        try:
            returncode = self.process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self.fail("Server did not shut down within 2 seconds of SIGINT")
        self.assertEqual(returncode, 0)

    def test_slow_client_receives_408(self):
        """A client that connects but never sends headers gets 408 Request Timeout."""
        s = socket.create_connection((HOST, PORT), timeout=2)
        s.settimeout(5)  # Give recv enough time to get the server's timeout response.

        # Hold the connection open without sending anything.
        # The server's 1-second timeout (CONNECTION_TIMEOUT env var) will fire first.
        time.sleep(1.5)

        response = s.recv(4096)
        s.close()
        self.assertIn(b"408", response)


if __name__ == "__main__":
    unittest.main()
