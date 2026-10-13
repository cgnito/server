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
        status, _ = route_request(make_request("GET", "/"))
        self.assertEqual(status, b"200 OK")

    def test_get_about_returns_200(self):
        status, _ = route_request(make_request("GET", "/about"))
        self.assertEqual(status, b"200 OK")

    def test_unknown_path_returns_404(self):
        status, _ = route_request(make_request("GET", "/nonexistent"))
        self.assertEqual(status, b"404 Not Found")

    def test_wrong_method_on_known_path_returns_404(self):
        # Current behaviour: POST / returns 404 instead of 405.
        # This will change when finding E1 is addressed.
        status, _ = route_request(make_request("POST", "/"))
        self.assertEqual(status, b"404 Not Found")

    def test_status_is_bytes(self):
        status, _ = route_request(make_request("GET", "/"))
        self.assertIsInstance(status, bytes)

    def test_body_is_bytes(self):
        _, body = route_request(make_request("GET", "/"))
        self.assertIsInstance(body, bytes)


if __name__ == "__main__":
    unittest.main()
