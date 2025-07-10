import pandas as pd
from binance import Client
import numpy as np
from binance.exceptions import BinanceAPIException, BinanceRequestException
from src.logger import binance_logger
import asyncio
import aiohttp
class HistoricalData:
    """Handles fetching historical data from Binance API with async support"""
    
    intervals = {
        "1s": Client.KLINE_INTERVAL_1SECOND,
        "1m": Client.KLINE_INTERVAL_1MINUTE,
        "1d": Client.KLINE_INTERVAL_1DAY,
        "1M": Client.KLINE_INTERVAL_1MONTH,
        "12h": Client.KLINE_INTERVAL_12HOUR,
        "1h": Client.KLINE_INTERVAL_1HOUR,
    }
    
    error_messages = {
        -1021: "Timestamp out of sync. Check system time.",
        -1022: "Invalid signature. Check API secret and request format.",
        -2014: "API key format invalid.",
        -2015: "Invalid API key, IP, or permissions.",
        -1003: "Too many requests. Rate limit exceeded.",
        -1013: "Invalid quantity or price filters.",
        -2010: "Account has insufficient balance.",
    }
    
    def __init__(self, api_key: str, api_secret: str) -> None:
        self.client = Client(api_key, api_secret)
        self.test_connection()
    
    def _process_kline_data(self, data: list) -> pd.DataFrame:
        """Process raw kline data into a structured DataFrame"""
        if not data:
            return pd.DataFrame()
            
        df = pd.DataFrame(
            data,
            columns=[
                "opentime",
                "open",
                "high", 
                "low",
                "close",
                "volume",
                "closetime",
                "quote_volume",  # Fixed duplicate 'volume' column
                "ntrades",
                "taker_buy_base_volume",
                "taker_buy_quote_volume",
                "ignore",
            ],
        )
        
        # Convert timestamps
        df["opentime"] = pd.to_datetime(df["opentime"], unit="ms")
        df["closetime"] = pd.to_datetime(df["closetime"], unit="ms")
        
        # Convert numeric columns
        numeric_cols = ["open", "high", "low", "close", "volume", "quote_volume"]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Calculate log returns with proper error handling
        df["log_returns"] = np.log(df["close"] / df["close"].shift(1))
        
        # Drop unnecessary columns
        df = df.drop([
            "ntrades",
            "taker_buy_base_volume", 
            "taker_buy_quote_volume",
            "ignore",
        ], axis=1)
        
        return df
    
    def get_kline(self, symbol: str, interval: str, limit: int = 500) -> pd.DataFrame:
        """Synchronous method to get kline data"""
        try:
            data = self.client.get_historical_klines(
                symbol, 
                self.intervals[interval], 
                limit=limit
            )
            return self._process_kline_data(data)
        except Exception as e:
            binance_logger.error(f"Error fetching data for {symbol} with interval {interval}: {e}")
            return pd.DataFrame()
    
    async def get_kline_async(self, symbol: str, interval: str, limit: int = 500) -> pd.DataFrame:
        """Asynchronous method to get kline data"""
        try:
            # Run the synchronous Binance client call in a thread pool
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None, 
                lambda: self.client.get_historical_klines(
                    symbol, 
                    self.intervals[interval], 
                    limit=limit
                )
            )
            return self._process_kline_data(data)
        except Exception as e:
            binance_logger.error(f"Error fetching data for {symbol} with interval {interval}: {e}")
            return pd.DataFrame()
    
    def save_data(self, data: pd.DataFrame, path: str) -> None:
        """Save DataFrame to CSV"""
        if not data.empty:
            data.to_csv(path, index=False)
    
    def test_connection(self) -> None:
        """Test the connection to Binance API"""
        try:
            self.client.get_account()
            binance_logger.info("Connection successful")
        except BinanceAPIException as e:
            error_msg = self.error_messages.get(e.code, f"Unknown error code: {e.code}")
            binance_logger.error(f"Diagnosis: {error_msg}")
            raise e
        except BinanceRequestException as e:
            binance_logger.error(f"Request Error: {e}")
            raise e