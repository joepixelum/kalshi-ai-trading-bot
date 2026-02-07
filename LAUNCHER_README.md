# Trading System Launcher Scripts

Two launcher scripts are provided to properly configure the environment and run both the trading bot and dashboard simultaneously.

## Quick Start

### Mac/Linux (Recommended)
```bash
cd kalshi-ai-trading-bot
./launch_trading_system.sh
```

### Cross-Platform (Python)
```bash
cd kalshi-ai-trading-bot
python launch_trading_system.py
```

## What These Scripts Do

Both launcher scripts perform the following steps automatically:

1. **Virtual Environment Check**
   - Verifies that `venv/` directory exists
   - Creates virtual environment if missing
   - Activates the virtual environment

2. **Environment Configuration**
   - Checks for `.env` file existence
   - Validates required API keys (KALSHI_API_KEY, XAI_API_KEY)
   - Loads environment variables

3. **Dependency Installation**
   - Upgrades pip to latest version
   - Installs all packages from `requirements.txt`
   - Installs dashboard requirements if available

4. **Database Initialization**
   - Checks if `trading_system.db` exists
   - Initializes database if not found
   - Uses `DatabaseManager` to create proper schema

5. **System Launch**
   - Starts trading bot (`beast_mode_bot.py`)
   - Starts dashboard (`trading_dashboard.py` on port 8501)
   - Monitors both processes
   - Gracefully handles shutdown on Ctrl+C

## Pre-requisites

Before running the launcher:

1. **Configure API Keys**
   ```bash
   cp env.template .env
   # Edit .env and add your API keys
   ```

2. **Ensure Python 3.8+**
   ```bash
   python3 --version
   ```

3. **Make Scripts Executable** (Mac/Linux only)
   ```bash
   chmod +x launch_trading_system.sh
   chmod +x launch_trading_system.py
   ```

## Usage

### Starting the System

**Shell Script (Mac/Linux):**
```bash
./launch_trading_system.sh
```

**Python Script (Cross-platform):**
```bash
python launch_trading_system.py
```

You should see output like:
```
============================================================
🚀 Kalshi Trading System Launcher
============================================================

ℹ️  Working directory: /path/to/kalshi-ai-trading-bot
✅ Virtual environment found
✅ Environment file configured
✅ Environment variables loaded
✅ Dependencies installed
✅ Database found
✅ All pre-flight checks passed!

ℹ️  Starting trading bot...
✅ Trading bot started (PID: 12345)
ℹ️  Starting dashboard...
✅ Dashboard started (PID: 12346)
ℹ️  Dashboard URL: http://localhost:8501

============================================================
System Running - Press Ctrl+C to stop
============================================================
```

### Stopping the System

Press **Ctrl+C** in the terminal where the launcher is running.

The launcher will gracefully shut down both the trading bot and dashboard.

### Accessing the Dashboard

Once running, open your browser to:
```
http://localhost:8501
```

## Log Files

The launcher creates/updates these log files:

- `logs/latest.log` - Trading bot main log
- `logs/bot_launcher.log` - Bot launcher output (shell script)
- `logs/dashboard_launcher.log` - Dashboard launcher output (shell script)

View logs in real-time:
```bash
tail -f logs/latest.log
```

## Troubleshooting

### Virtual Environment Issues

If you see `Virtual environment not found`:
```bash
python3 -m venv venv
```

### Missing Dependencies

If dependencies fail to install:
```bash
source venv/bin/activate  # Mac/Linux
# or
venv\Scripts\activate     # Windows

pip install --upgrade pip
pip install -r requirements.txt
```

### Database Issues

If database initialization fails:
```bash
rm trading_system.db  # Remove corrupted database
python -c "
import asyncio
from src.utils.database import DatabaseManager

async def main():
    db = DatabaseManager()
    await db.initialize()

asyncio.run(main())
"
```

### Port Already in Use

If port 8501 is already in use:
```bash
# Find and kill process using port 8501
lsof -ti:8501 | xargs kill -9
```

### Environment Variables Not Loading

Ensure `.env` file is in the correct location:
```bash
ls -la .env
cat .env | grep "KALSHI_API_KEY"
```

### Bot Exits Immediately

Check the logs:
```bash
tail -50 logs/latest.log
# or
cat logs/bot_launcher.log
```

Common issues:
- Invalid API keys in `.env`
- Missing `kalshi_private_key` file
- Database permissions issues

## Differences Between Scripts

### Shell Script (`launch_trading_system.sh`)

**Pros:**
- Native to Mac/Linux environments
- Faster execution
- Better process monitoring
- Uses `source` for virtual environment activation

**Cons:**
- Mac/Linux only (not Windows compatible)
- Requires bash shell

### Python Script (`launch_trading_system.py`)

**Pros:**
- Cross-platform (Mac/Linux/Windows)
- More portable
- Better error messages
- No shell dependencies

**Cons:**
- Slightly slower startup
- Requires Python 3.8+

## Advanced Usage

### Running Components Separately

If you want to run only the bot or dashboard:

**Bot Only:**
```bash
source venv/bin/activate
python beast_mode_bot.py
```

**Dashboard Only:**
```bash
source venv/bin/activate
streamlit run trading_dashboard.py
```

### Using Existing Commands Script

For individual operations, use the existing commands helper:
```bash
./commands.sh trade      # Run bot only
./commands.sh dashboard  # Run dashboard only
./commands.sh positions  # Check positions
./commands.sh balance    # Check balance
```

### Background Execution

To run the launcher in the background:

**Using nohup:**
```bash
nohup ./launch_trading_system.sh > launcher.log 2>&1 &
```

**Using screen:**
```bash
screen -S trading
./launch_trading_system.sh
# Press Ctrl+A, then D to detach
# screen -r trading to reattach
```

**Using tmux:**
```bash
tmux new -s trading
./launch_trading_system.sh
# Press Ctrl+B, then D to detach
# tmux attach -t trading to reattach
```

## Safety Notes

⚠️ **This system trades real money on Kalshi**

- Always review your `.env` configuration
- Check `LIVE_TRADING_ENABLED` setting
- Monitor logs regularly
- Set appropriate position limits in `src/config/settings.py`
- Use emergency stop if needed: `./commands.sh stop`

## Support

For issues or questions:
- Check logs in `logs/` directory
- Review `README.md` for system documentation
- See `COMMANDS_REFERENCE.md` for all available commands
- Consult `CLAUDE.md` for development guidance
