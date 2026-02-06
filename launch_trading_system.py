#!/usr/bin/env python3
"""
Trading System Launcher
Properly configures environment and launches both the trading bot and dashboard.
"""

import os
import sys
import subprocess
import time
import signal
from pathlib import Path
from typing import Optional

# ANSI color codes for terminal output
class Colors:
    BLUE = '\033[0;34m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    PURPLE = '\033[0;35m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color

def print_header(message: str):
    """Print a formatted header."""
    print(f"\n{Colors.BLUE}{'=' * 60}{Colors.NC}")
    print(f"{Colors.BLUE}{message}{Colors.NC}")
    print(f"{Colors.BLUE}{'=' * 60}{Colors.NC}\n")

def print_success(message: str):
    """Print a success message."""
    print(f"{Colors.GREEN}✅ {message}{Colors.NC}")

def print_error(message: str):
    """Print an error message."""
    print(f"{Colors.RED}❌ {message}{Colors.NC}")

def print_warning(message: str):
    """Print a warning message."""
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.NC}")

def print_info(message: str):
    """Print an info message."""
    print(f"{Colors.CYAN}ℹ️  {message}{Colors.NC}")

def check_virtual_environment() -> Optional[str]:
    """Check if virtual environment exists and return Python executable path."""
    venv_path = Path("venv")

    if not venv_path.exists():
        print_error("Virtual environment not found at ./venv/")
        print_info("Creating virtual environment...")
        try:
            subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
            print_success("Virtual environment created")
        except subprocess.CalledProcessError as e:
            print_error(f"Failed to create virtual environment: {e}")
            return None

    # Determine Python executable path based on OS
    if sys.platform == "win32":
        python_exe = venv_path / "Scripts" / "python.exe"
    else:
        python_exe = venv_path / "bin" / "python"

    if not python_exe.exists():
        print_error(f"Python executable not found at {python_exe}")
        return None

    print_success(f"Virtual environment found: {venv_path}")
    return str(python_exe)

def check_environment_file() -> bool:
    """Check if .env file exists with required variables."""
    env_file = Path(".env")

    if not env_file.exists():
        print_error(".env file not found")
        print_info("Copy env.template to .env and configure your API keys:")
        print_info("  cp env.template .env")
        return False

    # Check for required environment variables
    required_vars = ["KALSHI_API_KEY", "XAI_API_KEY"]
    missing_vars = []

    with open(env_file) as f:
        env_content = f.read()
        for var in required_vars:
            if f"{var}=" not in env_content or f"{var}=your_" in env_content:
                missing_vars.append(var)

    if missing_vars:
        print_warning(f"Missing or unconfigured environment variables: {', '.join(missing_vars)}")
        print_info("Please configure these in your .env file")
        return False

    print_success("Environment file configured")
    return True

def install_dependencies(python_exe: str) -> bool:
    """Install required dependencies."""
    print_info("Checking dependencies...")

    requirements_file = Path("requirements.txt")
    if not requirements_file.exists():
        print_error("requirements.txt not found")
        return False

    try:
        # Upgrade pip first
        subprocess.run(
            [python_exe, "-m", "pip", "install", "--upgrade", "pip"],
            capture_output=True,
            check=True
        )

        # Install requirements
        print_info("Installing dependencies (this may take a minute)...")
        subprocess.run(
            [python_exe, "-m", "pip", "install", "-r", "requirements.txt"],
            capture_output=True,
            check=True
        )

        # Install dashboard requirements if they exist
        dashboard_reqs = Path("dashboard_requirements.txt")
        if dashboard_reqs.exists():
            subprocess.run(
                [python_exe, "-m", "pip", "install", "-r", "dashboard_requirements.txt"],
                capture_output=True,
                check=True
            )

        print_success("Dependencies installed")
        return True

    except subprocess.CalledProcessError as e:
        print_error(f"Failed to install dependencies: {e}")
        return False

def check_database(python_exe: str) -> bool:
    """Check if database is initialized, initialize if needed."""
    db_file = Path("trading_system.db")

    if db_file.exists():
        print_success(f"Database found: {db_file}")
        return True

    print_warning("Database not found, initializing...")

    # Initialize database using DatabaseManager
    init_script = """
import asyncio
from src.utils.database import DatabaseManager

async def main():
    db = DatabaseManager()
    await db.initialize()
    print("Database initialized successfully")

asyncio.run(main())
"""

    try:
        result = subprocess.run(
            [python_exe, "-c", init_script],
            capture_output=True,
            text=True,
            check=True
        )
        print_success("Database initialized")
        return True

    except subprocess.CalledProcessError as e:
        print_error(f"Failed to initialize database: {e}")
        if e.stderr:
            print(e.stderr)
        return False

def load_environment():
    """Load environment variables from .env file."""
    env_file = Path(".env")
    if not env_file.exists():
        return

    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

    print_success("Environment variables loaded")

def launch_bot(python_exe: str) -> subprocess.Popen:
    """Launch the trading bot in a subprocess."""
    print_info("Starting trading bot...")

    # Load environment variables
    env = os.environ.copy()

    bot_process = subprocess.Popen(
        [python_exe, "beast_mode_bot.py"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    print_success("Trading bot started (PID: {})".format(bot_process.pid))
    return bot_process

def launch_dashboard(python_exe: str) -> subprocess.Popen:
    """Launch the Streamlit dashboard in a subprocess."""
    print_info("Starting dashboard...")

    # Load environment variables
    env = os.environ.copy()

    dashboard_process = subprocess.Popen(
        [
            python_exe, "-m", "streamlit", "run",
            "trading_dashboard.py",
            "--server.address", "localhost",
            "--server.port", "8501",
            "--browser.gatherUsageStats", "false",
            "--server.headless", "true"
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    print_success("Dashboard started (PID: {})".format(dashboard_process.pid))
    print_info("Dashboard URL: http://localhost:8501")
    return dashboard_process

def monitor_processes(bot_process: subprocess.Popen, dashboard_process: subprocess.Popen):
    """Monitor both processes and display their output."""
    print_header("System Running - Press Ctrl+C to stop")
    print_info("Trading bot logs: logs/latest.log")
    print_info("Dashboard: http://localhost:8501")
    print()

    try:
        while True:
            # Check if bot process is still running
            bot_poll = bot_process.poll()
            if bot_poll is not None:
                print_error(f"Trading bot exited with code {bot_poll}")
                # Read any remaining output
                if bot_process.stdout:
                    output = bot_process.stdout.read()
                    if output:
                        print(output)
                break

            # Check if dashboard process is still running
            dash_poll = dashboard_process.poll()
            if dash_poll is not None:
                print_error(f"Dashboard exited with code {dash_poll}")
                break

            # Read and display output from bot (non-blocking)
            if bot_process.stdout:
                try:
                    line = bot_process.stdout.readline()
                    if line:
                        print(f"[BOT] {line.rstrip()}")
                except:
                    pass

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n")
        print_warning("Shutting down...")

        # Gracefully terminate processes
        bot_process.terminate()
        dashboard_process.terminate()

        # Wait for processes to finish
        try:
            bot_process.wait(timeout=5)
            dashboard_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            bot_process.kill()
            dashboard_process.kill()

        print_success("System stopped")

def main():
    """Main launcher function."""
    print_header("🚀 Kalshi Trading System Launcher")

    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    print_info(f"Working directory: {script_dir}")

    # Step 1: Check virtual environment
    python_exe = check_virtual_environment()
    if not python_exe:
        print_error("Cannot proceed without virtual environment")
        return 1

    # Step 2: Check environment file
    if not check_environment_file():
        print_error("Cannot proceed without proper .env configuration")
        return 1

    # Step 3: Load environment variables
    load_environment()

    # Step 4: Install dependencies
    if not install_dependencies(python_exe):
        print_error("Cannot proceed without dependencies")
        return 1

    # Step 5: Check/initialize database
    if not check_database(python_exe):
        print_error("Cannot proceed without database")
        return 1

    print_success("All pre-flight checks passed!")
    print()

    # Step 6: Launch both bot and dashboard
    try:
        bot_process = launch_bot(python_exe)
        time.sleep(2)  # Give bot time to start

        dashboard_process = launch_dashboard(python_exe)
        time.sleep(3)  # Give dashboard time to start

        # Monitor both processes
        monitor_processes(bot_process, dashboard_process)

    except Exception as e:
        print_error(f"Error during launch: {e}")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
