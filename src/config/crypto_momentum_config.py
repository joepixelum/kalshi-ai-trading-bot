"""
Configuration for Cryptocurrency Momentum Arbitrage Strategy

This module defines configuration settings for the crypto momentum strategy that
tracks BTC/ETH price momentum before hourly Kalshi market settlement and enters
positions based on directional trend strength.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class CryptoMomentumStrategyConfig:
    """Configuration for crypto momentum arbitrage strategy"""

    # Strategy enable/disable
    enabled: bool = True

    # Capital allocation
    capital_allocation_pct: float = 0.20  # 20% of portfolio

    # Supported markets
    symbols: List[str] = field(default_factory=lambda: ["BTC", "ETH"])

    # Momentum thresholds
    momentum_threshold_5min_btc: float = 200.0  # $200 for BTC in 5 minutes
    momentum_threshold_5min_eth: float = 15.0   # $15 for ETH in 5 minutes
    momentum_threshold_10min_btc: float = 350.0  # $350 for BTC in 10 minutes
    momentum_threshold_10min_eth: float = 25.0   # $25 for ETH in 10 minutes

    # Entry criteria
    min_confidence_threshold: float = 0.70  # 70% minimum confidence to trade
    entry_window_seconds: int = 60  # Enter 60 seconds before hour close
    max_entry_window_seconds: int = 90  # Don't enter more than 90s before

    # Position management
    max_concurrent_positions: int = 8  # Max 8 crypto positions at once
    max_position_size_pct: float = 0.05  # Max 5% per position
    kelly_fraction: float = 0.75  # Kelly Criterion multiplier

    # Risk management
    win_rate_kill_switch: float = 0.65  # Disable strategy if win rate < 65%
    max_daily_loss_pct: float = 0.10  # Stop trading if lose 10% in a day
    min_trades_for_kill_switch: int = 20  # Need at least 20 trades before kill switch activates

    # WebSocket configuration
    exchanges: List[str] = field(default_factory=lambda: ["binance", "coinbase", "kraken"])
    price_history_seconds: int = 900  # Keep 15 minutes of price history
    reconnect_max_attempts: int = 5  # Max reconnection attempts
    reconnect_delay_base: float = 1.0  # Base delay for exponential backoff (seconds)

    # Monitoring
    scan_interval_seconds: int = 5  # Check markets every 5 seconds
    log_momentum_updates: bool = False  # Verbose momentum logging (for debugging)

    def get_momentum_threshold_5min(self, symbol: str) -> float:
        """Get 5-minute momentum threshold for given symbol"""
        if symbol == "BTC":
            return self.momentum_threshold_5min_btc
        elif symbol == "ETH":
            return self.momentum_threshold_5min_eth
        else:
            raise ValueError(f"Unknown symbol: {symbol}")

    def get_momentum_threshold_10min(self, symbol: str) -> float:
        """Get 10-minute momentum threshold for given symbol"""
        if symbol == "BTC":
            return self.momentum_threshold_10min_btc
        elif symbol == "ETH":
            return self.momentum_threshold_10min_eth
        else:
            raise ValueError(f"Unknown symbol: {symbol}")


# Production configuration (conservative)
PRODUCTION_CONFIG = CryptoMomentumStrategyConfig(
    enabled=True,
    capital_allocation_pct=0.20,
    symbols=["BTC", "ETH"],

    # Conservative thresholds for BTC
    momentum_threshold_5min_btc=200.0,
    momentum_threshold_10min_btc=350.0,

    # Conservative thresholds for ETH
    momentum_threshold_5min_eth=15.0,
    momentum_threshold_10min_eth=25.0,

    min_confidence_threshold=0.70,
    entry_window_seconds=60,
    max_concurrent_positions=8,
    max_position_size_pct=0.05,
    kelly_fraction=0.75,

    # Risk management
    win_rate_kill_switch=0.65,
    max_daily_loss_pct=0.10,

    # Exchanges
    exchanges=["binance", "coinbase", "kraken"],

    scan_interval_seconds=5
)


# Paper trading / testing configuration (more conservative)
TESTING_CONFIG = CryptoMomentumStrategyConfig(
    enabled=True,
    capital_allocation_pct=0.05,  # Only 5% for testing
    min_confidence_threshold=0.75,  # Higher confidence required
    max_concurrent_positions=3,  # Fewer concurrent positions
    log_momentum_updates=True,  # Enable verbose logging

    # Higher thresholds (more selective)
    momentum_threshold_5min_btc=250.0,
    momentum_threshold_10min_btc=400.0,
    momentum_threshold_5min_eth=20.0,
    momentum_threshold_10min_eth=30.0
)


# Aggressive configuration (for experienced use only)
AGGRESSIVE_CONFIG = CryptoMomentumStrategyConfig(
    enabled=True,
    capital_allocation_pct=0.30,  # 30% allocation (aggressive)
    min_confidence_threshold=0.60,  # Lower confidence threshold
    max_concurrent_positions=12,  # More positions

    # Lower thresholds (more trades)
    momentum_threshold_5min_btc=150.0,
    momentum_threshold_10min_btc=250.0,
    momentum_threshold_5min_eth=10.0,
    momentum_threshold_10min_eth=18.0,

    max_position_size_pct=0.08  # Larger positions
)
