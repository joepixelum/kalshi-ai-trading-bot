"""
Configuration settings for the Kalshi trading system.
Manages trading parameters, API configurations, and risk management settings.
"""

import os
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv
from enum import IntEnum

# Load environment variables
load_dotenv()


# =============================================================================
# RISK LEVEL SYSTEM (1-5)
# =============================================================================
# Level 1: Ultra Conservative - Minimal risk, few trades, high confidence required
# Level 2: Conservative - Low risk, selective trades
# Level 3: Moderate - Balanced risk/reward (DEFAULT)
# Level 4: Aggressive - Higher risk, more trades, lower thresholds
# Level 5: Ultra Aggressive - Maximum risk tolerance, trade frequently

class RiskLevel(IntEnum):
    ULTRA_CONSERVATIVE = 1
    CONSERVATIVE = 2
    MODERATE = 3
    AGGRESSIVE = 4
    ULTRA_AGGRESSIVE = 5


# Risk profile presets - each level adjusts key trading parameters
RISK_PROFILES = {
    RiskLevel.ULTRA_CONSERVATIVE: {
        "max_position_size_pct": 2.0,
        "max_daily_loss_pct": 5.0,
        "max_positions": 5,
        "min_confidence_to_trade": 0.75,
        "kelly_fraction": 0.25,
        "max_single_position": 0.02,
        "min_trade_edge": 0.20,
        "max_trades_per_hour": 10,
        "profit_threshold": 0.30,
        "loss_threshold": 0.08,
        "daily_ai_budget": 8.0,
    },
    RiskLevel.CONSERVATIVE: {
        "max_position_size_pct": 3.0,
        "max_daily_loss_pct": 8.0,
        "max_positions": 8,
        "min_confidence_to_trade": 0.65,
        "kelly_fraction": 0.40,
        "max_single_position": 0.03,
        "min_trade_edge": 0.15,
        "max_trades_per_hour": 20,
        "profit_threshold": 0.25,
        "loss_threshold": 0.10,
        "daily_ai_budget": 12.0,
    },
    RiskLevel.MODERATE: {
        "max_position_size_pct": 5.0,
        "max_daily_loss_pct": 12.0,
        "max_positions": 12,
        "min_confidence_to_trade": 0.55,
        "kelly_fraction": 0.55,
        "max_single_position": 0.04,
        "min_trade_edge": 0.10,
        "max_trades_per_hour": 30,
        "profit_threshold": 0.22,
        "loss_threshold": 0.12,
        "daily_ai_budget": 15.0,
    },
    RiskLevel.AGGRESSIVE: {
        "max_position_size_pct": 6.0,
        "max_daily_loss_pct": 15.0,
        "max_positions": 15,
        "min_confidence_to_trade": 0.50,
        "kelly_fraction": 0.70,
        "max_single_position": 0.05,
        "min_trade_edge": 0.08,
        "max_trades_per_hour": 40,
        "profit_threshold": 0.20,
        "loss_threshold": 0.15,
        "daily_ai_budget": 20.0,
    },
    RiskLevel.ULTRA_AGGRESSIVE: {
        "max_position_size_pct": 8.0,
        "max_daily_loss_pct": 20.0,
        "max_positions": 20,
        "min_confidence_to_trade": 0.45,
        "kelly_fraction": 0.85,
        "max_single_position": 0.07,
        "min_trade_edge": 0.05,
        "max_trades_per_hour": 60,
        "profit_threshold": 0.15,
        "loss_threshold": 0.18,
        "daily_ai_budget": 30.0,
    },
}

# Current risk level - can be set via environment variable or startup script
CURRENT_RISK_LEVEL = int(os.getenv("TRADING_RISK_LEVEL", "3"))


@dataclass
class APIConfig:
    """API configuration settings."""
    kalshi_api_key: str = field(default_factory=lambda: os.getenv("KALSHI_API_KEY", ""))
    kalshi_base_url: str = "https://api.elections.kalshi.com"  # Updated to new API endpoint
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    xai_api_key: str = field(default_factory=lambda: os.getenv("XAI_API_KEY", ""))
    openai_base_url: str = "https://api.openai.com/v1"


# Trading strategy configuration - INCREASED AGGRESSIVENESS
@dataclass
class TradingConfig:
    """Trading strategy configuration."""
    # Position sizing and risk management - MADE MORE AGGRESSIVE  
    max_position_size_pct: float = 5.0  # INCREASED: Back to 5% per position (was 3%)
    max_daily_loss_pct: float = 15.0    # INCREASED: Allow 15% daily loss (was 10%) 
    max_positions: int = 15              # INCREASED: Allow 15 concurrent positions (was 10)
    min_balance: float = 50.0           # REDUCED: Lower minimum to trade more (was 100)
    
    # Market filtering criteria - MUCH MORE PERMISSIVE
    min_volume: float = 200.0            # DECREASED: Much lower volume requirement (was 500, now 200)
    max_time_to_expiry_days: int = 30    # INCREASED: Allow longer timeframes (was 14, now 30)
    
    # AI decision making - MORE AGGRESSIVE THRESHOLDS
    min_confidence_to_trade: float = 0.50   # DECREASED: Lower confidence barrier (was 0.65, now 0.50)
    scan_interval_seconds: int = 30      # DECREASED: Scan more frequently (was 60, now 30)
    
    # AI model configuration
    primary_model: str = "grok-4" # DO NOT CHANGE THIS UNDER ANY CIRCUMSTANCES
    fallback_model: str = "grok-3"  # Fallback to available model
    ai_temperature: float = 0  # Lower temperature for more consistent JSON output
    ai_max_tokens: int = 8000    # Reasonable limit for reasoning models (grok-4 works better with 8000)
    
    # Position sizing (LEGACY - now using Kelly-primary approach)
    default_position_size: float = 3.0  # REDUCED: Now using Kelly Criterion as primary method (was 5%, now 3%)
    position_size_multiplier: float = 1.0  # Multiplier for AI confidence
    
    # Kelly Criterion settings (PRIMARY position sizing method) - MORE AGGRESSIVE
    use_kelly_criterion: bool = True        # Use Kelly Criterion for position sizing (PRIMARY METHOD)
    kelly_fraction: float = 0.75            # INCREASED: More aggressive Kelly multiplier (was 0.5, now 0.75)
    max_single_position: float = 0.05       # INCREASED: Higher position cap (was 0.03, now 5%)
    
    # Trading frequency - VERY AGGRESSIVE
    market_scan_interval: int = 15          # VERY FAST: Scan every 15 seconds (was 30)
    position_check_interval: int = 10       # VERY FAST: Check positions every 10 seconds (was 15)
    max_trades_per_hour: int = 40           # VERY HIGH: Allow many more trades per hour (was 20, now 40)
    run_interval_minutes: int = 5           # VERY FREQUENT: Run every 5 minutes (was 10)
    num_processor_workers: int = 5      # Number of concurrent market processor workers
    
    # Market selection preferences
    preferred_categories: List[str] = field(default_factory=lambda: [])
    excluded_categories: List[str] = field(default_factory=lambda: [])
    
    # High-confidence, near-expiry strategy
    enable_high_confidence_strategy: bool = True
    high_confidence_threshold: float = 0.95  # LLM confidence needed
    high_confidence_market_odds: float = 0.90 # Market price to look for
    high_confidence_expiry_hours: int = 24   # Max hours until expiry

    # Market probability filtering - exclude extreme probability markets
    # Markets above this probability are thinly traded and hard to execute
    max_market_probability: float = 0.95  # Exclude markets with >95% implied probability
    min_market_probability: float = 0.05  # Exclude markets with <5% implied probability

    # AI trading criteria - MORE PERMISSIVE
    max_analysis_cost_per_decision: float = 0.15  # INCREASED: Allow higher cost per decision (was 0.10, now 0.15)
    min_confidence_threshold: float = 0.45  # DECREASED: Lower confidence threshold (was 0.55, now 0.45)

    # Cost control and market analysis frequency - VERY PERMISSIVE FOR MORE TRADES
    daily_ai_budget: float = 20.0  # AGGRESSIVE: Much higher daily budget (was 10.0, now 20.0)
    max_ai_cost_per_decision: float = 0.12  # HIGHER: Allow more expensive analyses (was 0.08, now 0.12)
    analysis_cooldown_hours: int = 1  # VERY SHORT: Re-analyze markets hourly (was 3, now 1)
    max_analyses_per_market_per_day: int = 10  # VERY HIGH: Many re-analyses per day (was 4, now 10)
    
    # Daily AI spending limits - SAFETY CONTROLS
    daily_ai_cost_limit: float = 50.0  # Maximum daily spending on AI API calls (USD)
    enable_daily_cost_limiting: bool = True  # Enable daily cost limits
    sleep_when_limit_reached: bool = True  # Sleep until next day when limit reached

    # Enhanced market filtering to reduce analyses - MORE PERMISSIVE
    min_volume_for_ai_analysis: float = 200.0  # DECREASED: Much lower threshold (was 500, now 200)
    exclude_low_liquidity_categories: List[str] = field(default_factory=lambda: [
        # REMOVED weather and entertainment - trade all categories
    ])


@dataclass
class LoggingConfig:
    """Logging configuration."""
    log_level: str = "DEBUG"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_file: str = "logs/trading_system.log"
    enable_file_logging: bool = True
    enable_console_logging: bool = True
    max_log_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5


# BEAST MODE UNIFIED TRADING SYSTEM CONFIGURATION 🚀
# These settings control the advanced multi-strategy trading system

# === CAPITAL ALLOCATION ACROSS STRATEGIES ===
# Allocate capital across different trading approaches
# UPDATED: Rebalanced to accommodate new crypto momentum strategy
market_making_allocation: float = 0.32     # 32% for market making (spread profits) - was 40%
directional_allocation: float = 0.40       # 40% for directional trading (AI predictions) - was 50%
quick_flip_allocation: float = 0.24        # 24% for quick flip scalping - was 30%
arbitrage_allocation: float = 0.08         # 8% for arbitrage opportunities - was 10%
crypto_momentum_allocation: float = 0.20   # 20% for crypto momentum arbitrage - NEW

  # === PORTFOLIO OPTIMIZATION SETTINGS ===
# Kelly Criterion is now the PRIMARY position sizing method (moved to TradingConfig)
# total_capital: DYNAMICALLY FETCHED from Kalshi balance - never hardcoded!
use_risk_parity: bool = True            # Equal risk allocation vs equal capital
rebalance_hours: int = 6                # Rebalance portfolio every 6 hours
min_position_size: float = 5.0          # Minimum position size ($5 vs $10)
max_opportunities_per_batch: int = 50   # Limit opportunities to prevent optimization issues

# === RISK MANAGEMENT LIMITS ===
# Portfolio-level risk constraints (EXTREMELY RELAXED FOR TESTING)
max_volatility: float = 0.80            # Very high volatility allowed (80%)
max_correlation: float = 0.95           # Very high correlation allowed (95%)
max_drawdown: float = 0.50              # High drawdown tolerance (50%)
max_sector_exposure: float = 0.90       # Very high sector concentration (90%)

# === PERFORMANCE TARGETS ===
# System performance objectives - MORE AGGRESSIVE FOR MORE TRADES
target_sharpe: float = 0.3              # DECREASED: Lower Sharpe requirement (was 0.5, now 0.3)
target_return: float = 0.15             # INCREASED: Higher return target (was 0.10, now 0.15)
min_trade_edge: float = 0.08           # DECREASED: Lower edge requirement (was 0.15, now 8%)
min_confidence_for_large_size: float = 0.50  # DECREASED: Lower confidence requirement (was 0.65, now 50%)

# === DYNAMIC EXIT STRATEGIES ===
# Enhanced exit strategy settings - MORE AGGRESSIVE
use_dynamic_exits: bool = True
profit_threshold: float = 0.20          # DECREASED: Take profits sooner (was 0.25, now 0.20)
loss_threshold: float = 0.15            # INCREASED: Allow larger losses (was 0.10, now 0.15)
confidence_decay_threshold: float = 0.25  # INCREASED: Allow more confidence decay (was 0.20, now 0.25)
max_hold_time_hours: int = 240          # INCREASED: Hold longer (was 168, now 240 hours = 10 days)
volatility_adjustment: bool = True      # Adjust exits based on volatility

# === MARKET MAKING STRATEGY ===
# Settings for limit order market making - MORE AGGRESSIVE
enable_market_making: bool = True       # Enable market making strategy
min_spread_for_making: float = 0.01     # DECREASED: Accept smaller spreads (was 0.02, now 1¢)
max_inventory_risk: float = 0.15        # INCREASED: Allow higher inventory risk (was 0.10, now 15%)
order_refresh_minutes: int = 15         # Refresh orders every 15 minutes
max_orders_per_market: int = 4          # Maximum orders per market (2 each side)
max_market_making_per_cycle: int = 2    # THROTTLE: Max market making opportunities per cycle (prevents dominance)

# === CRYPTO MOMENTUM STRATEGY ===
# Settings for cryptocurrency momentum arbitrage
crypto_momentum_enabled: bool = True    # Enable crypto momentum strategy
crypto_momentum_symbols: List[str] = ["BTC", "ETH"]  # Symbols to track
crypto_momentum_min_confidence: float = 0.70  # Minimum confidence threshold (70%)
crypto_momentum_entry_window_sec: int = 60   # Enter 60 seconds before hour close
crypto_momentum_max_positions: int = 8       # Max concurrent crypto positions
crypto_momentum_win_rate_kill_switch: float = 0.65  # Disable if win rate < 65%
crypto_momentum_max_daily_loss_pct: float = 0.10    # Stop if lose 10% in a day
crypto_momentum_scan_interval_sec: int = 5   # Check markets every 5 seconds

# === MARKET SELECTION (ENHANCED FOR MORE OPPORTUNITIES) ===
# Removed time restrictions - trade ANY deadline with dynamic exits!
# max_time_to_expiry_days: REMOVED      # No longer used - trade any timeline!
min_volume_for_analysis: float = 200.0  # DECREASED: Much lower minimum volume (was 1000, now 200)
min_volume_for_market_making: float = 500.0  # DECREASED: Lower volume for market making (was 2000, now 500)
min_price_movement: float = 0.02        # DECREASED: Lower minimum range (was 0.05, now 2¢)
max_bid_ask_spread: float = 0.15        # INCREASED: Allow wider spreads (was 0.10, now 15¢)
min_confidence_long_term: float = 0.45  # DECREASED: Lower confidence for distant expiries (was 0.65, now 45%)

# === COST OPTIMIZATION (MORE GENEROUS) ===
# Enhanced cost controls for the beast mode system
daily_ai_budget: float = 15.0           # INCREASED: Higher budget for more opportunities (was 10.0, now 15.0)
max_ai_cost_per_decision: float = 0.12  # INCREASED: Higher per-decision limit (was 0.08, now 0.12)
analysis_cooldown_hours: int = 2        # DECREASED: Much shorter cooldown (was 4, now 2)
max_analyses_per_market_per_day: int = 6  # INCREASED: More analyses per day (was 3, now 6)
skip_news_for_low_volume: bool = True   # Skip expensive searches for low volume
news_search_volume_threshold: float = 1000.0  # News threshold

# === SYSTEM BEHAVIOR ===
# Overall system behavior settings
beast_mode_enabled: bool = True         # Enable the unified advanced system
fallback_to_legacy: bool = True         # Fallback to legacy system if needed
live_trading_enabled: bool = True       # Set to True for live trading
paper_trading_mode: bool = False        # Paper trading for testing
log_level: str = "INFO"                 # Logging level
performance_monitoring: bool = True     # Enable performance monitoring

# === ADVANCED FEATURES ===
# Cutting-edge features for maximum performance
cross_market_arbitrage: bool = False    # Enable when arbitrage module ready
multi_model_ensemble: bool = False      # Use multiple AI models (future)
sentiment_analysis: bool = False        # News sentiment analysis (future)
options_strategies: bool = False        # Complex options strategies (future)
algorithmic_execution: bool = False     # Smart order execution (future)


@dataclass
class Settings:
    """Main settings class combining all configuration."""
    api: APIConfig = field(default_factory=APIConfig)
    trading: TradingConfig = field(default_factory=TradingConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    risk_level: int = field(default_factory=lambda: CURRENT_RISK_LEVEL)

    def validate(self) -> bool:
        """Validate configuration settings."""
        if not self.api.kalshi_api_key:
            raise ValueError("KALSHI_API_KEY environment variable is required")

        if not self.api.xai_api_key:
            raise ValueError("XAI_API_KEY environment variable is required")

        if self.trading.max_position_size_pct <= 0 or self.trading.max_position_size_pct > 100:
            raise ValueError("max_position_size_pct must be between 0 and 100")

        if self.trading.min_confidence_to_trade <= 0 or self.trading.min_confidence_to_trade > 1:
            raise ValueError("min_confidence_to_trade must be between 0 and 1")

        return True

    def apply_risk_level(self, level: int) -> None:
        """
        Apply a risk level (1-5) to adjust trading parameters.

        Level 1: Ultra Conservative - Minimal risk, few trades
        Level 2: Conservative - Low risk, selective trades
        Level 3: Moderate - Balanced risk/reward (DEFAULT)
        Level 4: Aggressive - Higher risk, more trades
        Level 5: Ultra Aggressive - Maximum risk tolerance
        """
        if level < 1 or level > 5:
            raise ValueError(f"Risk level must be 1-5, got {level}")

        self.risk_level = level
        risk_level_enum = RiskLevel(level)
        profile = RISK_PROFILES[risk_level_enum]

        # Apply profile settings to TradingConfig
        self.trading.max_position_size_pct = profile["max_position_size_pct"]
        self.trading.max_daily_loss_pct = profile["max_daily_loss_pct"]
        self.trading.max_positions = profile["max_positions"]
        self.trading.min_confidence_to_trade = profile["min_confidence_to_trade"]
        self.trading.kelly_fraction = profile["kelly_fraction"]
        self.trading.max_single_position = profile["max_single_position"]
        self.trading.max_trades_per_hour = profile["max_trades_per_hour"]
        self.trading.daily_ai_budget = profile["daily_ai_budget"]

        # Also update module-level settings
        global min_trade_edge, profit_threshold, loss_threshold, daily_ai_budget
        min_trade_edge = profile["min_trade_edge"]
        profit_threshold = profile["profit_threshold"]
        loss_threshold = profile["loss_threshold"]
        daily_ai_budget = profile["daily_ai_budget"]

    def get_risk_level_name(self) -> str:
        """Get human-readable name for current risk level."""
        names = {
            1: "Ultra Conservative",
            2: "Conservative",
            3: "Moderate",
            4: "Aggressive",
            5: "Ultra Aggressive"
        }
        return names.get(self.risk_level, "Unknown")


# Global settings instance
settings = Settings()

# Apply risk level from environment on startup
try:
    settings.apply_risk_level(CURRENT_RISK_LEVEL)
    print(f"🎚️  Risk Level: {CURRENT_RISK_LEVEL} ({settings.get_risk_level_name()})")
except ValueError as e:
    print(f"Invalid risk level: {e}, using default (3)")
    settings.apply_risk_level(3)

# Validate settings on import
try:
    settings.validate()
except ValueError as e:
    print(f"Configuration validation error: {e}")
    print("Please check your environment variables and configuration.") 