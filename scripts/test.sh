#!/bin/sh
# Run the full test suite from any working directory.

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_DIR=$(dirname "$SCRIPT_DIR")

cd "$PROJECT_DIR" || exit 1
exec python3 -m unittest discover -s tests -p "test_*.py" -v