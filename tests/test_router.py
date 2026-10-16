"""
Unit tests for router.py.

Tests that requests are matched to the correct status and body.
No socket or server process is needed.
"""

import unittest

from router import route_request


def make_request(method: str, target: str) -> dict:
    """Return a minimal request dict for routing tests."""
    return {
        "method": method,
        "target": target,
        "version": "HTTP/1.1",
        "headers": {},
        "body": b"",
    }


class TestRouteRequest(unittest.TestCase):

    def test_get_root_returns_200(self):
        status, _, content_type = route_request(make_request("GET", "/"))
        self.assertEqual(status, b"200 OK")
        self.assertEqual(content_type, b"text/plain")

    def test_get_about_returns_200(self):
        status, _, content_type = route_request(make_request("GET", "/about"))
        self.assertEqual(status, b"200 OK")
        self.assertEqual(content_type, b"text/plain")

    def test_get_json_returns_json_content_type(self):
        status, body, content_type = route_request(make_request("GET", "/json"))
        self.assertEqual(status, b"200 OK")
        self.assertEqual(body, b'{"message": "Hello from JSON"}')
        self.assertEqual(content_type, b"application/json")

    def test_get_html_returns_html_content_type(self):
        status, body, content_type = route_request(make_request("GET", "/html"))
        self.assertEqual(status, b"200 OK")
        self.assertEqual(body, b"<h1>Hello from HTML</h1>")
        self.assertEqual(content_type, b"text/html")

    def test_unknown_path_returns_404(self):
        status, _, content_type = route_request(make_request("GET", "/nonexistent"))
        self.assertEqual(status, b"404 Not Found")
        self.assertEqual(content_type, b"text/plain")

    def test_wrong_method_on_known_path_returns_404(self):
        # Current behaviour: POST / returns 404 instead of 405.
        # This will change when finding E1 is addressed.
        status, _, content_type = route_request(make_request("POST", "/"))
        self.assertEqual(status, b"404 Not Found")
        self.assertEqual(content_type, b"text/plain")

    def test_status_is_bytes(self):
        status, _, _ = route_request(make_request("GET", "/"))
        self.assertIsInstance(status, bytes)

    def test_body_is_bytes(self):
        _, body, _ = route_request(make_request("GET", "/"))
        self.assertIsInstance(body, bytes)


if __name__ == "__main__":
    unittest.main()
