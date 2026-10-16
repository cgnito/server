"""
Unit tests for structured access-log formatting.
"""

import json
import unittest

from access_log import format_access_log


class TestFormatAccessLog(unittest.TestCase):

    def test_formats_request_and_response_fields_as_json(self):
        request = {
            "method": "GET",
            "target": "/json",
            "version": "HTTP/1.1",
        }
        line = format_access_log(request, b"200 OK", b"{}")
        record = json.loads(line)

        self.assertEqual(
            record,
            {
                "method": "GET",
                "target": "/json",
                "version": "HTTP/1.1",
                "status": "200 OK",
                "content_length": 2,
            },
        )

    def test_formats_missing_request_fields_as_null(self):
        line = format_access_log(None, b"400 Bad Request", b"Bad Request")
        record = json.loads(line)

        self.assertIsNone(record["method"])
        self.assertIsNone(record["target"])
        self.assertIsNone(record["version"])
        self.assertEqual(record["status"], "400 Bad Request")
        self.assertEqual(record["content_length"], 11)


if __name__ == "__main__":
    unittest.main()
