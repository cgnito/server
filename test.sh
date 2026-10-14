#!/bin/sh
# Run the full test suite.
# run from the server/ directory so that module imports
# resolve correctly for both the test files and the server subprocess
# started by integration tests.

cd "$(dirname "$0")"
python3 -m unittest discover -s tests -p "test_*.py" -v
