#!/bin/bash
# Test runner script for stock-ticker CLI

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=================================="
echo "Stock Ticker CLI Test Suite"
echo "=================================="
echo ""

# Check if pytest is installed
if ! python3 -m pytest --version > /dev/null 2>&1; then
    echo -e "${RED}✗ pytest not found${NC}"
    echo "Installing test dependencies..."
    pip install -r requirements.txt
fi

# Parse command line arguments
TEST_CATEGORY="$1"

case "$TEST_CATEGORY" in
    unit)
        echo -e "${YELLOW}Running unit tests...${NC}"
        python3 -m pytest -m unit -v
        ;;
    integration)
        echo -e "${YELLOW}Running integration tests...${NC}"
        python3 -m pytest -m integration -v
        ;;
    cli)
        echo -e "${YELLOW}Running CLI tests...${NC}"
        python3 -m pytest -m cli -v
        ;;
    database)
        echo -e "${YELLOW}Running database tests...${NC}"
        python3 -m pytest -m database -v
        ;;
    api)
        echo -e "${YELLOW}Running API mock tests...${NC}"
        python3 -m pytest -m api -v
        ;;
    coverage)
        echo -e "${YELLOW}Running tests with coverage...${NC}"
        python3 -m pytest --cov=src/stock_ticker --cov-report=term-missing --cov-report=html -v
        echo ""
        echo -e "${GREEN}Coverage report generated: coverage_html/index.html${NC}"
        ;;
    fast)
        echo -e "${YELLOW}Running fast tests only...${NC}"
        python3 -m pytest -m "unit and not slow" -v
        ;;
    *)
        echo -e "${YELLOW}Running all tests...${NC}"
        python3 -m pytest -v
        ;;
esac

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
else
    echo -e "${RED}✗ Some tests failed${NC}"
fi

echo ""
echo "Test runner usage:"
echo "  ./test.sh           # Run all tests"
echo "  ./test.sh unit      # Run unit tests only"
echo "  ./test.sh integration   # Run integration tests"
echo "  ./test.sh cli       # Run CLI tests"
echo "  ./test.sh coverage  # Run with coverage report"
echo "  ./test.sh fast      # Run fast tests only"

exit $EXIT_CODE
