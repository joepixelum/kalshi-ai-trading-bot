"""
Cryptocurrency Momentum Arbitrage Strategy

Tracks BTC/ETH price momentum in the minutes before Kalshi hourly market settlement
and enters positions when strong directional trends are detected.

Strategy Logic:
1. Monitor crypto prices 5-10 minutes before hourly market close
2. Calculate momentum indicators (price change, volume, volatility)
3. Score confidence that momentum will continue through settlement
4. Enter trades 30-60 seconds before market close if confidence > threshold
"""

import asyncio
import statistics
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from src.clients.crypto_price_feed_client import CryptoPriceFeedClient, PricePoint
from src.clients.kalshi_client import KalshiClient
from src.config.crypto_momentum_config import CryptoMomentumStrategyConfig
from src.utils.database import DatabaseManager, Market, Position
from src.utils.logging_setup import get_trading_logger


@dataclass
class MomentumSignal:
    """Momentum signal calculated from price history"""
    symbol: str
    current_price: float
    price_change_5min: float  # Absolute change in dollars
    price_change_10min: float
    pct_change_5min: float  # Percentage change
    pct_change_10min: float
    momentum_strength: float  # Normalized 0-1
    momentum_direction: str  # "up" or "down"
    volume_acceleration: float  # Change in volume (if available)
    volatility: float  # Recent price volatility
    timestamp: datetime


@dataclass
class CryptoMomentumResults:
    """Results from crypto momentum strategy execution"""
    positions_created: int = 0
    total_capital_used: float = 0.0
    expected_profit: float = 0.0
    avg_confidence: float = 0.0
    markets_analyzed: int = 0
    opportunities_found: int = 0


class CryptoMomentumStrategy:
    """
    Cryptocurrency momentum arbitrage strategy for Kalshi hourly markets.
    """

    def __init__(
        self,
        config: CryptoMomentumStrategyConfig,
        db_manager: DatabaseManager,
        kalshi_client: KalshiClient,
        price_feed_client: CryptoPriceFeedClient
    ):
        self.config = config
        self.db_manager = db_manager
        self.kalshi_client = kalshi_client
        self.price_feed = price_feed_client
        self.logger = get_trading_logger("crypto_momentum")

        self.logger.info(
            f"Crypto momentum strategy initialized: "
            f"enabled={config.enabled}, "
            f"symbols={config.symbols}, "
            f"min_confidence={config.min_confidence_threshold}"
        )

    async def execute_crypto_momentum_trades(
        self,
        available_capital: float
    ) -> CryptoMomentumResults:
        """
        Main execution method for crypto momentum strategy.

        Args:
            available_capital: Capital allocated to this strategy

        Returns:
            CryptoMomentumResults with execution summary
        """
        if not self.config.enabled:
            self.logger.info("Crypto momentum strategy is disabled")
            return CryptoMomentumResults()

        # Check kill switch conditions
        if await self._check_kill_switch():
            self.logger.warning("Kill switch activated - strategy disabled")
            return CryptoMomentumResults()

        results = CryptoMomentumResults()

        try:
            # Scan for upcoming hourly markets (closing in 60-90 seconds)
            upcoming_markets = await self._scan_upcoming_markets()
            results.markets_analyzed = len(upcoming_markets)

            if not upcoming_markets:
                self.logger.debug("No upcoming crypto markets found")
                return results

            self.logger.info(f"Found {len(upcoming_markets)} upcoming crypto markets")

            # Analyze each market for momentum opportunities
            for market in upcoming_markets:
                # Extract symbol from market (BTC or ETH)
                symbol = self._extract_symbol_from_market(market)
                if not symbol or symbol not in self.config.symbols:
                    continue

                # Calculate momentum signal
                momentum_signal = await self._calculate_momentum(symbol)
                if not momentum_signal:
                    continue

                # Calculate confidence
                confidence = self._calculate_confidence(momentum_signal)

                if self.config.log_momentum_updates:
                    self.logger.debug(
                        f"🪙 Momentum: {symbol} "
                        f"5min: ${momentum_signal.price_change_5min:.2f} ({momentum_signal.pct_change_5min:.2%}), "
                        f"Direction: {momentum_signal.momentum_direction}, "
                        f"Confidence: {confidence:.1%}"
                    )

                # Determine if we should enter a trade
                should_trade, side, position_size = await self._should_enter_trade(
                    market, momentum_signal, confidence, available_capital
                )

                if should_trade:
                    results.opportunities_found += 1

                    # Execute trade
                    success = await self._execute_trade(
                        market, symbol, side, position_size, momentum_signal, confidence
                    )

                    if success:
                        results.positions_created += 1
                        results.total_capital_used += position_size
                        results.expected_profit += position_size * 0.40  # Assume 40% return on wins
                        results.avg_confidence = (
                            (results.avg_confidence * (results.positions_created - 1) + confidence)
                            / results.positions_created
                        )

            self.logger.info(
                f"🪙 Crypto momentum execution complete: "
                f"{results.positions_created} positions created from "
                f"{results.opportunities_found} opportunities"
            )

        except Exception as e:
            self.logger.error(f"Error in crypto momentum execution: {e}", exc_info=True)

        return results

    async def _scan_upcoming_markets(self) -> List[Market]:
        """
        Find Kalshi crypto markets closing in the next 60-90 seconds.

        Returns:
            List of Market objects
        """
        try:
            # Get all crypto markets from Kalshi
            # Filter by category or ticker pattern (KXBTC, KXETH, etc.)
            all_markets = await self.db_manager.get_eligible_markets(
                volume_min=0  # No volume filter for crypto markets
            )

            upcoming = []
            now = datetime.now()

            for market in all_markets:
                # Check if this is a crypto market
                if not self._is_crypto_market(market):
                    continue

                # Calculate time to expiry
                expiry_time = datetime.fromtimestamp(market.expiration_ts)
                time_to_expiry = (expiry_time - now).total_seconds()

                # Check if within entry window
                if (self.config.entry_window_seconds <= time_to_expiry
                    <= self.config.max_entry_window_seconds):
                    upcoming.append(market)

            return upcoming

        except Exception as e:
            self.logger.error(f"Error scanning upcoming markets: {e}")
            return []

    def _is_crypto_market(self, market: Market) -> bool:
        """Check if a market is a crypto hourly market"""
        # Kalshi crypto markets typically have tickers like:
        # KXBTCUSD-24JAN-1400 (BTC hourly)
        # KXETHUSD-24JAN-1400 (ETH hourly)
        ticker = market.market_id.upper()
        return "BTC" in ticker or "ETH" in ticker

    def _extract_symbol_from_market(self, market: Market) -> Optional[str]:
        """Extract crypto symbol (BTC or ETH) from market ticker"""
        ticker = market.market_id.upper()
        if "BTC" in ticker:
            return "BTC"
        elif "ETH" in ticker:
            return "ETH"
        return None

    async def _calculate_momentum(self, symbol: str) -> Optional[MomentumSignal]:
        """
        Calculate momentum indicators from price history.

        Args:
            symbol: Crypto symbol (BTC or ETH)

        Returns:
            MomentumSignal or None if insufficient data
        """
        try:
            # Get 10 minutes of price history
            prices = await self.price_feed.get_price_history(symbol, seconds=600)

            if len(prices) < 60:  # Need at least 60 data points (1 minute)
                self.logger.warning(f"Insufficient price data for {symbol}: {len(prices)} points")
                return None

            # Get current price
            current_price = prices[-1].price

            # Find price 5 minutes ago
            price_5min_ago = self._get_price_at_time(prices, seconds_ago=300)
            if not price_5min_ago:
                return None

            # Find price 10 minutes ago (if available)
            price_10min_ago = self._get_price_at_time(prices, seconds_ago=600)
            if not price_10min_ago:
                price_10min_ago = price_5min_ago  # Fallback

            # Calculate price changes
            change_5min = current_price - price_5min_ago
            change_10min = current_price - price_10min_ago

            pct_change_5min = (change_5min / price_5min_ago) * 100
            pct_change_10min = (change_10min / price_10min_ago) * 100

            # Determine direction and strength
            direction = "up" if change_5min > 0 else "down"

            # Get momentum threshold for this symbol
            threshold = self.config.get_momentum_threshold_5min(symbol)
            strength = min(abs(change_5min) / threshold, 1.0)

            # Calculate volume acceleration (if volume data available)
            volume_accel = self._calculate_volume_acceleration(prices)

            # Calculate volatility (standard deviation of recent prices)
            volatility = self._calculate_volatility(prices)

            return MomentumSignal(
                symbol=symbol,
                current_price=current_price,
                price_change_5min=change_5min,
                price_change_10min=change_10min,
                pct_change_5min=pct_change_5min,
                pct_change_10min=pct_change_10min,
                momentum_strength=strength,
                momentum_direction=direction,
                volume_acceleration=volume_accel,
                volatility=volatility,
                timestamp=datetime.now()
            )

        except Exception as e:
            self.logger.error(f"Error calculating momentum for {symbol}: {e}")
            return None

    def _get_price_at_time(self, prices: List[PricePoint], seconds_ago: int) -> Optional[float]:
        """Get price from N seconds ago"""
        if not prices:
            return None

        target_time = datetime.now() - timedelta(seconds=seconds_ago)

        # Find closest price point to target time
        closest = min(prices, key=lambda p: abs((p.timestamp - target_time).total_seconds()))

        # Only use if within 30 seconds of target
        if abs((closest.timestamp - target_time).total_seconds()) <= 30:
            return closest.price

        return None

    def _calculate_volume_acceleration(self, prices: List[PricePoint]) -> float:
        """Calculate volume acceleration (change in recent volume)"""
        try:
            # Get last 60 seconds and previous 60 seconds
            recent_volume = sum(p.volume for p in prices[-60:] if p.volume > 0)
            older_volume = sum(p.volume for p in prices[-120:-60] if p.volume > 0)

            if older_volume == 0:
                return 0.0

            return (recent_volume - older_volume) / older_volume

        except Exception:
            return 0.0

    def _calculate_volatility(self, prices: List[PricePoint]) -> float:
        """Calculate recent price volatility (standard deviation)"""
        try:
            recent_prices = [p.price for p in prices[-60:]]  # Last 60 seconds
            if len(recent_prices) < 2:
                return 0.0

            return statistics.stdev(recent_prices)

        except Exception:
            return 0.0

    def _calculate_confidence(self, momentum_signal: MomentumSignal) -> float:
        """
        Calculate confidence that momentum will continue through settlement.

        Args:
            momentum_signal: Calculated momentum signal

        Returns:
            Confidence score (0.0 to 1.0)
        """
        # Start with base confidence from momentum strength
        confidence = 0.50 + (momentum_signal.momentum_strength * 0.30)

        # Boost for accelerating momentum (5min change > 10min change)
        if abs(momentum_signal.pct_change_5min) > abs(momentum_signal.pct_change_10min):
            confidence += 0.10  # Momentum is accelerating

        # Boost for volume confirmation
        if momentum_signal.volume_acceleration > 0.20:
            confidence += 0.05  # Volume increasing

        # Penalize high volatility (increases uncertainty)
        if momentum_signal.volatility > 50.0:  # Arbitrary threshold
            confidence -= 0.10

        # Cap at 0.90 (never 100% certain)
        return min(max(confidence, 0.0), 0.90)

    async def _should_enter_trade(
        self,
        market: Market,
        momentum_signal: MomentumSignal,
        confidence: float,
        available_capital: float
    ) -> Tuple[bool, str, float]:
        """
        Determine if we should enter a trade.

        Returns:
            (should_trade, side, position_size)
        """
        # Check confidence threshold
        if confidence < self.config.min_confidence_threshold:
            return False, "", 0.0

        # Check position limits
        open_positions = await self.db_manager.get_open_live_positions()
        crypto_positions = [p for p in open_positions if p.strategy == "crypto_momentum"]

        if len(crypto_positions) >= self.config.max_concurrent_positions:
            self.logger.warning(
                f"Max crypto positions ({self.config.max_concurrent_positions}) reached"
            )
            return False, "", 0.0

        # Determine side based on momentum direction
        # If momentum is UP, bet YES (price will be higher)
        # If momentum is DOWN, bet NO (price will be lower)
        side = "YES" if momentum_signal.momentum_direction == "up" else "NO"

        # Calculate position size using Kelly Criterion
        position_size = self._calculate_position_size(
            confidence, available_capital
        )

        # Check if position size is viable
        if position_size < 5.0:  # Minimum $5 position
            return False, "", 0.0

        return True, side, position_size

    def _calculate_position_size(self, confidence: float, available_capital: float) -> float:
        """
        Calculate position size using Kelly Criterion.

        Args:
            confidence: Win probability (0.0 to 1.0)
            available_capital: Capital available for this strategy

        Returns:
            Position size in dollars
        """
        # Kelly Criterion: f = (bp - q) / b
        # where:
        # - b = odds received (assume 1:1 for simplicity)
        # - p = probability of winning (confidence)
        # - q = probability of losing (1 - confidence)

        win_prob = confidence
        lose_prob = 1 - confidence
        odds = 1.0  # Assume 1:1 odds for simplicity

        kelly_fraction = (odds * win_prob - lose_prob) / odds

        # Apply Kelly fraction multiplier for safety
        fractional_kelly = kelly_fraction * self.config.kelly_fraction

        # Calculate position size
        position_size = available_capital * fractional_kelly

        # Cap at max position size percentage
        max_position = available_capital * self.config.max_position_size_pct
        position_size = min(position_size, max_position)

        return max(0.0, position_size)

    async def _execute_trade(
        self,
        market: Market,
        symbol: str,
        side: str,
        position_size: float,
        momentum_signal: MomentumSignal,
        confidence: float
    ) -> bool:
        """
        Execute a crypto momentum trade.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Calculate quantity (number of contracts)
            # Kalshi contracts are in cents, position_size is in dollars
            entry_price = market.yes_price if side == "YES" else market.no_price
            quantity = int(position_size / entry_price) if entry_price > 0 else 0

            if quantity < 1:
                self.logger.warning(f"Quantity too small: {quantity}")
                return False

            self.logger.info(
                f"🪙 CRYPTO TRADE: {side} {market.market_id} "
                f"@ ${entry_price:.2f}, "
                f"Qty: {quantity}, "
                f"Size: ${position_size:.2f}, "
                f"Momentum: ${momentum_signal.price_change_5min:.2f}, "
                f"Confidence: {confidence:.1%}"
            )

            # Create position in database
            position = Position(
                market_id=market.market_id,
                side=side,
                entry_price=entry_price,
                quantity=quantity,
                timestamp=datetime.now(),
                status="live",
                confidence=confidence,
                strategy="crypto_momentum",
                stop_loss_price=None,  # Will be set by position tracking
                take_profit_price=None,  # Will be set by position tracking
                max_hold_hours=24  # Exit within 24 hours if not settled
            )

            await self.db_manager.add_position(position)

            # Log crypto-specific trade data
            await self._log_crypto_trade(market, symbol, momentum_signal, confidence, position)

            return True

        except Exception as e:
            self.logger.error(f"Error executing trade: {e}", exc_info=True)
            return False

    async def _log_crypto_trade(
        self,
        market: Market,
        symbol: str,
        momentum_signal: MomentumSignal,
        confidence: float,
        position: Position
    ) -> None:
        """Log crypto-specific trade data to database"""
        # This would insert into the crypto_momentum_trades table
        # For now, we'll just log it
        self.logger.info(
            f"Logged crypto trade: market={market.market_id}, "
            f"symbol={symbol}, "
            f"momentum_5min=${momentum_signal.price_change_5min:.2f}, "
            f"confidence={confidence:.2%}"
        )

    async def _check_kill_switch(self) -> bool:
        """
        Check if kill switch should be activated based on recent win rate.

        Returns:
            True if kill switch activated (strategy should stop)
        """
        try:
            # Get recent crypto momentum trades (last 7 days)
            # For now, check all positions with strategy='crypto_momentum'
            all_positions = await self.db_manager.get_all_positions()
            crypto_positions = [
                p for p in all_positions
                if p.strategy == "crypto_momentum"
                and p.status == "closed"
                and p.timestamp >= datetime.now() - timedelta(days=7)
            ]

            if len(crypto_positions) < self.config.min_trades_for_kill_switch:
                return False  # Not enough data

            # Calculate win rate
            wins = sum(1 for p in crypto_positions if p.pnl and p.pnl > 0)
            win_rate = wins / len(crypto_positions)

            if win_rate < self.config.win_rate_kill_switch:
                self.logger.error(
                    f"🚨 CRYPTO MOMENTUM KILL SWITCH ACTIVATED: "
                    f"Win rate {win_rate:.1%} < {self.config.win_rate_kill_switch:.1%} "
                    f"({len(crypto_positions)} trades)"
                )
                self.config.enabled = False
                return True

            return False

        except Exception as e:
            self.logger.error(f"Error checking kill switch: {e}")
            return False
