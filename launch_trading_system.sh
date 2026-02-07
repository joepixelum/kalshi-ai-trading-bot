#!/bin/bash

# 🚀 Kalshi Trading System Launcher
# Properly configures environment and launches both bot and dashboard

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default risk level (1-5, default is 3 = Moderate)
RISK_LEVEL="${1:-3}"

# Process IDs for cleanup
BOT_PID=""
DASHBOARD_PID=""

# Cleanup function
cleanup() {
    echo ""
    echo -e "${YELLOW}⚠️  Shutting down...${NC}"

    if [ ! -z "$BOT_PID" ]; then
        echo -e "${CYAN}Stopping trading bot (PID: $BOT_PID)...${NC}"
        kill $BOT_PID 2>/dev/null || true
    fi

    if [ ! -z "$DASHBOARD_PID" ]; then
        echo -e "${CYAN}Stopping dashboard (PID: $DASHBOARD_PID)...${NC}"
        kill $DASHBOARD_PID 2>/dev/null || true
    fi

    # Also kill any streamlit processes on port 8501
    lsof -ti:8501 | xargs kill -9 2>/dev/null || true

    echo -e "${GREEN}✅ System stopped${NC}"
    exit 0
}

# Set up trap for cleanup
trap cleanup SIGINT SIGTERM

print_header() {
    echo ""
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${CYAN}ℹ️  $1${NC}"
}

# Risk level names
get_risk_level_name() {
    case $1 in
        1) echo "Ultra Conservative" ;;
        2) echo "Conservative" ;;
        3) echo "Moderate" ;;
        4) echo "Aggressive" ;;
        5) echo "Ultra Aggressive" ;;
        *) echo "Unknown" ;;
    esac
}

# Display usage
show_usage() {
    echo ""
    echo -e "${CYAN}Usage: $0 [RISK_LEVEL]${NC}"
    echo ""
    echo "RISK_LEVEL (1-5):"
    echo "  1 = Ultra Conservative - Minimal risk, few trades, high confidence required"
    echo "  2 = Conservative       - Low risk, selective trades"
    echo "  3 = Moderate           - Balanced risk/reward (DEFAULT)"
    echo "  4 = Aggressive         - Higher risk, more trades, lower thresholds"
    echo "  5 = Ultra Aggressive   - Maximum risk tolerance, trade frequently"
    echo ""
    echo "Examples:"
    echo "  $0       # Runs with risk level 3 (Moderate)"
    echo "  $0 2     # Runs with risk level 2 (Conservative)"
    echo "  $0 4     # Runs with risk level 4 (Aggressive)"
    echo ""
}

# Main launcher
main() {
    # Validate risk level
    if [[ "$RISK_LEVEL" == "-h" || "$RISK_LEVEL" == "--help" ]]; then
        show_usage
        exit 0
    fi

    if ! [[ "$RISK_LEVEL" =~ ^[1-5]$ ]]; then
        print_error "Invalid risk level: $RISK_LEVEL (must be 1-5)"
        show_usage
        exit 1
    fi

    RISK_NAME=$(get_risk_level_name $RISK_LEVEL)

    print_header "🚀 Kalshi Trading System Launcher"
    echo -e "${PURPLE}🎚️  Risk Level: $RISK_LEVEL ($RISK_NAME)${NC}"
    echo ""

    # Get script directory and change to it
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    cd "$SCRIPT_DIR"
    print_info "Working directory: $SCRIPT_DIR"

    # Step 1: Check virtual environment
    print_info "Checking virtual environment..."
    if [ ! -d "venv" ]; then
        print_error "Virtual environment not found at ./venv/"
        print_info "Creating virtual environment..."
        python3 -m venv venv
        print_success "Virtual environment created"
    else
        print_success "Virtual environment found"
    fi

    # Step 2: Activate virtual environment
    print_info "Activating virtual environment..."
    source venv/bin/activate
    print_success "Virtual environment activated"

    # Verify Python executable
    PYTHON_EXE="$(which python)"
    print_info "Using Python: $PYTHON_EXE"

    # Step 3: Check .env file
    print_info "Checking environment configuration..."
    if [ ! -f ".env" ]; then
        print_error ".env file not found"
        print_info "Copy env.template to .env and configure your API keys:"
        print_info "  cp env.template .env"
        exit 1
    fi

    # Check for required variables
    if ! grep -q "KALSHI_API_KEY=" .env || grep -q "KALSHI_API_KEY=your_" .env; then
        print_warning "KALSHI_API_KEY not configured in .env"
    fi

    if ! grep -q "XAI_API_KEY=" .env || grep -q "XAI_API_KEY=your_" .env; then
        print_warning "XAI_API_KEY not configured in .env"
    fi

    print_success "Environment file found"

    # Step 4: Load environment variables
    print_info "Loading environment variables..."
    set -a  # Automatically export all variables
    source .env
    set +a

    # Export risk level for Python to pick up
    export TRADING_RISK_LEVEL="$RISK_LEVEL"
    print_success "Environment variables loaded (Risk Level: $RISK_LEVEL)"

    # Step 5: Install dependencies
    print_info "Checking dependencies..."
    pip install --upgrade pip -q
    pip install -r requirements.txt -q

    if [ -f "dashboard_requirements.txt" ]; then
        pip install -r dashboard_requirements.txt -q
    fi

    print_success "Dependencies installed"

    # Step 6: Check database
    print_info "Checking database..."
    if [ ! -f "trading_system.db" ]; then
        print_warning "Database not found, initializing..."
        python -c "
import asyncio
from src.utils.database import DatabaseManager

async def main():
    db = DatabaseManager()
    await db.initialize()
    print('Database initialized successfully')

asyncio.run(main())
"
        print_success "Database initialized"
    else
        print_success "Database found"
    fi

    print_success "All pre-flight checks passed!"
    echo ""

    # Step 7: Launch trading bot
    print_info "Starting trading bot..."
    python beast_mode_bot.py > logs/bot_launcher.log 2>&1 &
    BOT_PID=$!
    sleep 2

    if ps -p $BOT_PID > /dev/null; then
        print_success "Trading bot started (PID: $BOT_PID)"
    else
        print_error "Trading bot failed to start"
        print_info "Check logs/bot_launcher.log for details"
        exit 1
    fi

    # Step 8: Launch dashboard
    print_info "Starting dashboard..."
    python -m streamlit run trading_dashboard.py \
        --server.address localhost \
        --server.port 8501 \
        --browser.gatherUsageStats false \
        --server.headless true > logs/dashboard_launcher.log 2>&1 &
    DASHBOARD_PID=$!
    sleep 3

    if ps -p $DASHBOARD_PID > /dev/null; then
        print_success "Dashboard started (PID: $DASHBOARD_PID)"
        print_info "Dashboard URL: http://localhost:8501"
    else
        print_error "Dashboard failed to start"
        print_info "Check logs/dashboard_launcher.log for details"
        kill $BOT_PID 2>/dev/null || true
        exit 1
    fi

    # Step 9: Monitor processes
    print_header "System Running - Press Ctrl+C to stop"
    echo -e "${PURPLE}🎚️  Risk Level: $RISK_LEVEL ($RISK_NAME)${NC}"
    print_info "Trading bot PID: $BOT_PID"
    print_info "Dashboard PID: $DASHBOARD_PID"
    print_info "Trading bot logs: logs/latest.log"
    print_info "Dashboard: http://localhost:8501"
    echo ""

    # Monitor both processes
    while true; do
        # Check if bot is still running
        if ! ps -p $BOT_PID > /dev/null 2>&1; then
            print_error "Trading bot stopped unexpectedly"
            print_info "Check logs/bot_launcher.log and logs/latest.log for details"
            kill $DASHBOARD_PID 2>/dev/null || true
            exit 1
        fi

        # Check if dashboard is still running
        if ! ps -p $DASHBOARD_PID > /dev/null 2>&1; then
            print_error "Dashboard stopped unexpectedly"
            print_info "Check logs/dashboard_launcher.log for details"
            kill $BOT_PID 2>/dev/null || true
            exit 1
        fi

        sleep 5
    done
}

# Run main function
main
