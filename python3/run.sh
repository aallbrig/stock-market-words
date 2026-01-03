#!/bin/bash
# Convenience wrapper to run the CLI with the virtual environment

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    echo "Installing package in development mode..."
    pip install -q -e .
else
    source venv/bin/activate
fi

# Run the CLI with all arguments
ticker-cli "$@"
