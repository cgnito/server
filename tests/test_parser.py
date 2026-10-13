"""
Unit tests for http_parser.py.

Tests parse_request_line, parse_request, and read_request_body using
static bytes — no live socket required.
"""

import unittest

from http_parser import parse_request, parse_request_line, read_request_body


class TestParseRequestLine(unittest.TestCase):
    """Tests for the request-line parser (method SP target SP version)."""

    def test_valid_get(self):
        result = parse_request_line("GET / HTTP/1.1")
        self.assertEqual(result["method"], "GET")
        self.assertEqual(result["target"], "/")
        self.assertEqual(result["version"], "HTTP/1.1")

    def test_valid_post(self):
        result = parse_request_line("POST /submit HTTP/1.1")
        self.assertEqual(result["method"], "POST")
        self.assertEqual(result["target"], "/submit")

    def test_http_10_is_accepted(self):
        result = parse_request_line("GET / HTTP/1.0")
        self.assertEqual(result["version"], "HTTP/1.0")

    def test_too_few_parts_raises(self):
        with self.assertRaises(ValueError):
            parse_request_line("GET /")

    def test_too_many_parts_raises(self):
        with self.assertRaises(ValueError):
            parse_request_line("GET / HTTP/1.1 extra")

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            parse_request_line("")

    def test_unsupported_version_raises(self):
        with self.assertRaises(ValueError):
            parse_request_line("GET / HTTP/2.0")

    def test_method_with_digit_raises(self):
        with self.assertRaises(ValueError):
            parse_request_line("G3T / HTTP/1.1")

    def test_extra_space_in_request_line_raises(self):
        # "GET  / HTTP/1.1" splits into 4 parts, not 3.
        with self.assertRaises(ValueError):
            parse_request_line("GET  / HTTP/1.1")


class TestParseRequest(unittest.TestCase):
    """Tests for the full request parser (request line + headers + body bytes)."""

    def test_get_with_no_body(self):
        raw = b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n"
        result = parse_request(raw)
        self.assertEqual(result["method"], "GET")
        self.assertEqual(result["target"], "/")
        self.assertEqual(result["version"], "HTTP/1.1")
        self.assertEqual(result["body"], b"")

    def test_header_names_are_lowercased(self):
        raw = b"GET / HTTP/1.1\r\nContent-Type: text/plain\r\nHost: localhost\r\n\r\n"
        result = parse_request(raw)
        self.assertIn("content-type", result["headers"])
        self.assertNotIn("Content-Type", result["headers"])

    def test_header_value_whitespace_is_stripped(self):
        raw = b"GET / HTTP/1.1\r\nHost:   localhost   \r\n\r\n"
        result = parse_request(raw)
        self.assertEqual(result["headers"]["host"], "localhost")

    def test_body_bytes_already_in_buffer_are_preserved(self):
        # Bytes that arrived after \r\n\r\n in the same recv are kept.
        raw = b"POST / HTTP/1.1\r\nHost: localhost\r\n\r\nHello"
        result = parse_request(raw)
        self.assertEqual(result["body"], b"Hello")

    def test_missing_header_terminator_raises(self):
        raw = b"GET / HTTP/1.1\r\nHost: localhost"
        with self.assertRaises(ValueError):
            parse_request(raw)

    def test_header_without_colon_raises(self):
        raw = b"GET / HTTP/1.1\r\nBadHeader\r\n\r\n"
        with self.assertRaises(ValueError):
            parse_request(raw)

    def test_empty_header_name_raises(self):
        raw = b"GET / HTTP/1.1\r\n: value\r\n\r\n"
        with self.assertRaises(ValueError):
            parse_request(raw)

    def test_duplicate_header_raises(self):
        # Current behaviour: duplicates are rejected.
        # This will be relaxed when finding B2 is addressed.
        raw = b"GET / HTTP/1.1\r\nHost: a\r\nHost: b\r\n\r\n"
        with self.assertRaises(ValueError):
            parse_request(raw)


class TestReadRequestBody(unittest.TestCase):
    """Tests for the body reader, using a minimal socket stand-in."""

    class _FakeSocket:
        """A fake socket whose recv() returns bytes from a fixed payload."""

        def __init__(self, payload: bytes):
            self._payload = payload
            self._pos = 0

        def recv(self, n: int) -> bytes:
            chunk = self._payload[self._pos : self._pos + n]
            self._pos += n
            return chunk

    def test_no_content_length_header_reads_nothing(self):
        request = {"headers": {}, "body": b""}
        sock = self._FakeSocket(b"")
        result = read_request_body(sock, request)
        self.assertEqual(result["body"], b"")

    def test_reads_full_body_from_socket(self):
        request = {"headers": {"content-length": "5"}, "body": b""}
        sock = self._FakeSocket(b"Hello")
        result = read_request_body(sock, request)
        self.assertEqual(result["body"], b"Hello")

    def test_body_already_fully_in_buffer_needs_no_socket_read(self):
        # Body arrived with the headers in the first recv; socket has nothing more.
        request = {"headers": {"content-length": "5"}, "body": b"Hello"}
        sock = self._FakeSocket(b"")
        result = read_request_body(sock, request)
        self.assertEqual(result["body"], b"Hello")

    def test_body_split_across_buffer_and_socket(self):
        # 2 bytes already in the buffer, 3 more come from the socket.
        request = {"headers": {"content-length": "5"}, "body": b"He"}
        sock = self._FakeSocket(b"llo")
        result = read_request_body(sock, request)
        self.assertEqual(result["body"], b"Hello")

    def test_connection_closes_before_body_complete_raises(self):
        request = {"headers": {"content-length": "10"}, "body": b""}
        sock = self._FakeSocket(b"")  # Socket gives nothing — simulates early close.
        with self.assertRaises(ConnectionError):
            read_request_body(sock, request)


if __name__ == "__main__":
    unittest.main()
