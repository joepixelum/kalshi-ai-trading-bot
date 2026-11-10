"""
Cryptocurrency Price Feed Client

Real-time cryptocurrency price feeds via WebSocket connections to multiple exchanges.
Provides aggregated price data for BTC and ETH with automatic reconnection and
price history buffering for momentum calculations.
"""

import asyncio
import json
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Deque
import aiohttp

from src.utils.logging_setup import get_trading_logger


@dataclass
class PricePoint:
    """A single price data point from an exchange"""
    timestamp: datetime
    exchange: str
    symbol: str
    price: float
    volume: float = 0.0  # Not all exchanges provide volume


@dataclass
class ExchangeConnection:
    """Metadata for an active WebSocket connection"""
    exchange: str
    websocket: Optional[aiohttp.ClientWebSocketResponse]
    symbols: List[str]
    last_heartbeat: datetime
    reconnect_attempts: int
    is_connected: bool


class CryptoPriceFeedClient:
    """
    Client for real-time cryptocurrency price feeds from multiple exchanges.

    Connects to Binance, Coinbase, and Kraken WebSocket APIs to aggregate
    real-time price data for BTC and ETH.
    """

    def __init__(self, reconnect_max_attempts: int = 5, reconnect_delay_base: float = 1.0):
        self.logger = get_trading_logger("crypto_price_feed")

        # WebSocket connections
        self.connections: Dict[str, ExchangeConnection] = {}

        # Price history buffers (circular deques)
        # Key: (exchange, symbol), Value: deque of PricePoints
        self.price_history: Dict[tuple, Deque[PricePoint]] = {}
        self.price_history_seconds = 900  # 15 minutes default

        # Latest prices for quick access
        # Key: (exchange, symbol), Value: latest PricePoint
        self.latest_prices: Dict[tuple, PricePoint] = {}

        # Reconnection settings
        self.reconnect_max_attempts = reconnect_max_attempts
        self.reconnect_delay_base = reconnect_delay_base

        # Lock for thread-safe price updates
        self.price_lock = asyncio.Lock()

        # Background tasks
        self.listener_tasks = []
        self.shutdown_event = asyncio.Event()

    async def connect_all_exchanges(self, symbols: List[str]) -> None:
        """
        Connect to all configured exchanges for the given symbols.

        Args:
            symbols: List of symbols to track (e.g., ["BTC", "ETH"])
        """
        self.logger.info(f"Connecting to crypto exchanges for symbols: {symbols}")

        # Connect to each exchange concurrently
        await asyncio.gather(
            self.connect_binance(symbols),
            self.connect_coinbase(symbols),
            self.connect_kraken(symbols)
        )

        self.logger.info("All exchange connections established")

    async def connect_binance(self, symbols: List[str]) -> None:
        """Connect to Binance WebSocket API"""
        exchange = "binance"

        try:
            # Binance WebSocket URL format: wss://stream.binance.com:9443/stream?streams=symbol@ticker
            # Example: btcusdt@ticker, ethusdt@ticker
            streams = "/".join([f"{symbol.lower()}usdt@ticker" for symbol in symbols])
            url = f"wss://stream.binance.com:9443/stream?streams={streams}"

            session = aiohttp.ClientSession()
            websocket = await session.ws_connect(url)

            self.connections[exchange] = ExchangeConnection(
                exchange=exchange,
                websocket=websocket,
                symbols=symbols,
                last_heartbeat=datetime.now(),
                reconnect_attempts=0,
                is_connected=True
            )

            # Initialize price history buffers
            for symbol in symbols:
                key = (exchange, symbol)
                self.price_history[key] = deque(maxlen=self.price_history_seconds)

            # Start listener task
            task = asyncio.create_task(self._listen_binance())
            self.listener_tasks.append(task)

            self.logger.info(f"Connected to Binance: {symbols}")

        except Exception as e:
            self.logger.error(f"Failed to connect to Binance: {e}")
            await self._schedule_reconnect(exchange, symbols)

    async def connect_coinbase(self, symbols: List[str]) -> None:
        """Connect to Coinbase WebSocket API"""
        exchange = "coinbase"

        try:
            url = "wss://ws-feed.exchange.coinbase.com"

            session = aiohttp.ClientSession()
            websocket = await session.ws_connect(url)

            # Coinbase requires subscription message
            # Product IDs: BTC-USD, ETH-USD
            product_ids = [f"{symbol}-USD" for symbol in symbols]
            subscribe_message = {
                "type": "subscribe",
                "product_ids": product_ids,
                "channels": ["ticker"]
            }
            await websocket.send_json(subscribe_message)

            self.connections[exchange] = ExchangeConnection(
                exchange=exchange,
                websocket=websocket,
                symbols=symbols,
                last_heartbeat=datetime.now(),
                reconnect_attempts=0,
                is_connected=True
            )

            # Initialize price history buffers
            for symbol in symbols:
                key = (exchange, symbol)
                self.price_history[key] = deque(maxlen=self.price_history_seconds)

            # Start listener task
            task = asyncio.create_task(self._listen_coinbase())
            self.listener_tasks.append(task)

            self.logger.info(f"Connected to Coinbase: {symbols}")

        except Exception as e:
            self.logger.error(f"Failed to connect to Coinbase: {e}")
            await self._schedule_reconnect(exchange, symbols)

    async def connect_kraken(self, symbols: List[str]) -> None:
        """Connect to Kraken WebSocket API"""
        exchange = "kraken"

        try:
            url = "wss://ws.kraken.com"

            session = aiohttp.ClientSession()
            websocket = await session.ws_connect(url)

            # Kraken subscription message
            # Pairs: XBT/USD (Bitcoin), ETH/USD
            pairs = []
            for symbol in symbols:
                if symbol == "BTC":
                    pairs.append("XBT/USD")
                elif symbol == "ETH":
                    pairs.append("ETH/USD")

            subscribe_message = {
                "event": "subscribe",
                "pair": pairs,
                "subscription": {"name": "ticker"}
            }
            await websocket.send_json(subscribe_message)

            self.connections[exchange] = ExchangeConnection(
                exchange=exchange,
                websocket=websocket,
                symbols=symbols,
                last_heartbeat=datetime.now(),
                reconnect_attempts=0,
                is_connected=True
            )

            # Initialize price history buffers
            for symbol in symbols:
                key = (exchange, symbol)
                self.price_history[key] = deque(maxlen=self.price_history_seconds)

            # Start listener task
            task = asyncio.create_task(self._listen_kraken())
            self.listener_tasks.append(task)

            self.logger.info(f"Connected to Kraken: {symbols}")

        except Exception as e:
            self.logger.error(f"Failed to connect to Kraken: {e}")
            await self._schedule_reconnect(exchange, symbols)

    async def _listen_binance(self) -> None:
        """Listen for Binance WebSocket messages"""
        exchange = "binance"
        connection = self.connections.get(exchange)

        if not connection or not connection.websocket:
            return

        try:
            async for msg in connection.websocket:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)

                    # Binance ticker format: {"stream":"btcusdt@ticker","data":{"c":"95000.50",...}}
                    if "data" in data:
                        ticker = data["data"]
                        symbol_raw = data.get("stream", "").split("@")[0]

                        # Extract symbol (btcusdt -> BTC)
                        if symbol_raw.endswith("usdt"):
                            symbol = symbol_raw.replace("usdt", "").upper()
                        else:
                            continue

                        # Parse price
                        price = float(ticker.get("c", 0))  # 'c' is close price (latest)
                        volume = float(ticker.get("v", 0))  # 'v' is 24h volume

                        await self._handle_price_update(exchange, symbol, price, volume)

                    connection.last_heartbeat = datetime.now()

                elif msg.type == aiohttp.WSMsgType.ERROR:
                    self.logger.error(f"Binance WebSocket error: {msg.data}")
                    break

        except Exception as e:
            self.logger.error(f"Error in Binance listener: {e}")
        finally:
            connection.is_connected = False
            await self._schedule_reconnect(exchange, connection.symbols)

    async def _listen_coinbase(self) -> None:
        """Listen for Coinbase WebSocket messages"""
        exchange = "coinbase"
        connection = self.connections.get(exchange)

        if not connection or not connection.websocket:
            return

        try:
            async for msg in connection.websocket:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)

                    # Coinbase ticker format: {"type":"ticker","product_id":"BTC-USD","price":"95000.50",...}
                    if data.get("type") == "ticker":
                        product_id = data.get("product_id", "")
                        symbol = product_id.split("-")[0]  # BTC-USD -> BTC

                        price = float(data.get("price", 0))
                        volume = float(data.get("volume_24h", 0))

                        await self._handle_price_update(exchange, symbol, price, volume)

                    connection.last_heartbeat = datetime.now()

                elif msg.type == aiohttp.WSMsgType.ERROR:
                    self.logger.error(f"Coinbase WebSocket error: {msg.data}")
                    break

        except Exception as e:
            self.logger.error(f"Error in Coinbase listener: {e}")
        finally:
            connection.is_connected = False
            await self._schedule_reconnect(exchange, connection.symbols)

    async def _listen_kraken(self) -> None:
        """Listen for Kraken WebSocket messages"""
        exchange = "kraken"
        connection = self.connections.get(exchange)

        if not connection or not connection.websocket:
            return

        try:
            async for msg in connection.websocket:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)

                    # Kraken ticker format: [channelID, {"c":["95000.50",...]}, "ticker", "XBT/USD"]
                    if isinstance(data, list) and len(data) == 4:
                        ticker = data[1]
                        pair = data[3]  # "XBT/USD" or "ETH/USD"

                        # Extract symbol
                        if pair == "XBT/USD":
                            symbol = "BTC"
                        elif pair == "ETH/USD":
                            symbol = "ETH"
                        else:
                            continue

                        # Parse price ('c' is last trade closed array: [price, volume])
                        price = float(ticker.get("c", [0])[0])
                        volume = float(ticker.get("v", [0])[0])  # 'v' is volume

                        await self._handle_price_update(exchange, symbol, price, volume)

                    connection.last_heartbeat = datetime.now()

                elif msg.type == aiohttp.WSMsgType.ERROR:
                    self.logger.error(f"Kraken WebSocket error: {msg.data}")
                    break

        except Exception as e:
            self.logger.error(f"Error in Kraken listener: {e}")
        finally:
            connection.is_connected = False
            await self._schedule_reconnect(exchange, connection.symbols)

    async def _handle_price_update(self, exchange: str, symbol: str, price: float, volume: float) -> None:
        """Process and store a price update"""
        async with self.price_lock:
            price_point = PricePoint(
                timestamp=datetime.now(),
                exchange=exchange,
                symbol=symbol,
                price=price,
                volume=volume
            )

            key = (exchange, symbol)

            # Update latest price
            self.latest_prices[key] = price_point

            # Add to price history
            if key in self.price_history:
                self.price_history[key].append(price_point)

    async def _schedule_reconnect(self, exchange: str, symbols: List[str]) -> None:
        """Schedule reconnection attempt with exponential backoff"""
        connection = self.connections.get(exchange)
        if not connection:
            return

        if connection.reconnect_attempts >= self.reconnect_max_attempts:
            self.logger.error(
                f"Max reconnection attempts ({self.reconnect_max_attempts}) "
                f"reached for {exchange}. Giving up."
            )
            return

        # Exponential backoff delay
        delay = self.reconnect_delay_base * (2 ** connection.reconnect_attempts)
        connection.reconnect_attempts += 1

        self.logger.warning(
            f"Scheduling reconnect to {exchange} in {delay:.1f}s "
            f"(attempt {connection.reconnect_attempts}/{self.reconnect_max_attempts})"
        )

        await asyncio.sleep(delay)

        # Reconnect
        if exchange == "binance":
            await self.connect_binance(symbols)
        elif exchange == "coinbase":
            await self.connect_coinbase(symbols)
        elif exchange == "kraken":
            await self.connect_kraken(symbols)

    async def get_current_price(self, symbol: str, exchange: Optional[str] = None) -> Optional[float]:
        """
        Get the latest price for a symbol.

        Args:
            symbol: Symbol (BTC or ETH)
            exchange: Specific exchange or None for aggregated price

        Returns:
            Latest price or None if unavailable
        """
        if exchange:
            # Get price from specific exchange
            key = (exchange, symbol)
            price_point = self.latest_prices.get(key)
            return price_point.price if price_point else None
        else:
            # Get aggregated price (simple average across exchanges)
            return await self.calculate_aggregated_price(symbol)

    async def get_price_history(self, symbol: str, seconds: int = 600,
                               exchange: Optional[str] = None) -> List[PricePoint]:
        """
        Get historical prices for a symbol.

        Args:
            symbol: Symbol (BTC or ETH)
            seconds: Number of seconds of history to return
            exchange: Specific exchange or None for all exchanges

        Returns:
            List of PricePoint objects
        """
        async with self.price_lock:
            cutoff_time = datetime.now() - timedelta(seconds=seconds)
            results = []

            if exchange:
                # Get from specific exchange
                key = (exchange, symbol)
                if key in self.price_history:
                    results = [p for p in self.price_history[key] if p.timestamp >= cutoff_time]
            else:
                # Get from all exchanges
                for key, history in self.price_history.items():
                    ex, sym = key
                    if sym == symbol:
                        results.extend([p for p in history if p.timestamp >= cutoff_time])

            # Sort by timestamp
            results.sort(key=lambda p: p.timestamp)
            return results

    async def calculate_aggregated_price(self, symbol: str) -> Optional[float]:
        """
        Calculate aggregated price across all exchanges (simple average).

        Args:
            symbol: Symbol (BTC or ETH)

        Returns:
            Aggregated price or None if no data available
        """
        prices = []
        for exchange in ["binance", "coinbase", "kraken"]:
            key = (exchange, symbol)
            price_point = self.latest_prices.get(key)
            if price_point and price_point.price > 0:
                prices.append(price_point.price)

        if not prices:
            return None

        # Simple average (could be weighted by volume in the future)
        return sum(prices) / len(prices)

    def get_connection_status(self) -> Dict[str, bool]:
        """Get connection status for all exchanges"""
        return {
            exchange: conn.is_connected
            for exchange, conn in self.connections.items()
        }

    async def close(self) -> None:
        """Close all WebSocket connections gracefully"""
        self.logger.info("Closing all crypto price feed connections")

        self.shutdown_event.set()

        # Cancel listener tasks
        for task in self.listener_tasks:
            task.cancel()

        # Close WebSocket connections
        for connection in self.connections.values():
            if connection.websocket and not connection.websocket.closed:
                await connection.websocket.close()

        self.logger.info("All crypto price feed connections closed")
