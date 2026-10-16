"""
Unit tests for response.py.

Tests that build_response assembles a valid HTTP/1.1 response byte string.
"""

import unittest

from response import build_response


class TestBuildResponse(unittest.TestCase):
    """Tests for the HTTP response assembler."""

    def test_status_line_starts_response(self):
        response = build_response(b"200 OK", b"")
        self.assertTrue(response.startswith(b"HTTP/1.1 200 OK\r\n"))

    def test_content_length_matches_body(self):
        body = b"Hello, world!"  # 13 bytes
        response = build_response(b"200 OK", body)
        self.assertIn(b"Content-Length: 13\r\n", response)

    def test_empty_body_produces_zero_content_length(self):
        response = build_response(b"200 OK", b"")
        self.assertIn(b"Content-Length: 0\r\n", response)

    def test_body_appears_after_blank_line(self):
        body = b"Test body"
        response = build_response(b"200 OK", body)
        self.assertTrue(response.endswith(body))

    def test_headers_end_with_double_crlf(self):
        response = build_response(b"200 OK", b"anything")
        self.assertIn(b"\r\n\r\n", response)

    def test_connection_close_header_is_present(self):
        response = build_response(b"200 OK", b"")
        self.assertIn(b"Connection: close\r\n", response)

    def test_custom_content_type_is_used(self):
        response = build_response(b"200 OK", b"{}", content_type=b"application/json")
        self.assertIn(b"Content-Type: application/json\r\n", response)
        self.assertNotIn(b"Content-Type: text/plain\r\n", response)

    def test_custom_headers_are_used(self):
        response = build_response(
            b"405 Method Not Allowed",
            b"Method Not Allowed",
            headers={b"Allow": b"GET"},
        )
        self.assertIn(b"Allow: GET\r\n", response)

    def test_404_response(self):
        response = build_response(b"404 Not Found", b"Not Found")
        self.assertIn(b"HTTP/1.1 404 Not Found", response)
        self.assertTrue(response.endswith(b"Not Found"))

    def test_500_response(self):
        response = build_response(b"500 Internal Server Error", b"Internal Server Error")
        self.assertIn(b"HTTP/1.1 500 Internal Server Error", response)


if __name__ == "__main__":
    unittest.main()
