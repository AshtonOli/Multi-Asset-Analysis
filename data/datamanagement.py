import pandas as pd
import datetime as dt
from data.binance_connector import HistoricalData
from src.util import parse_json
import random
from typing import Dict, Union, List, Optional
from functools import reduce
import numpy as np
from src.logger import data_management_logger
import colorsys
import asyncio


def get_random_color() -> str:
    """Generate a random hex color"""
    h = random.random()
    s = 0.5 + random.random() / 2.0  # Saturation between 0.5 and 1.0
    v = 0.5 + random.random() / 2.0  # Value between 0.5 and 1.0

    rgb = colorsys.hsv_to_rgb(h, s, v)
    return f"#{int(rgb[0] * 255):02x}{int(rgb[1] * 255):02x}{int(rgb[2] * 255):02x}"


def find_earliest_datetime_key(
    datetime_dict: Dict[str, dt.datetime], return_all: bool = False
) -> Union[str, List[str], None]:
    """
    Find key(s) with the earliest datetime value

    Args:
        datetime_dict: Dictionary with datetime values
        return_all: If True, return all keys with minimum value; if False, return first one

    Returns:
        Single key (str), list of keys, or None if dict is empty
    """
    if not datetime_dict:
        return None

    min_datetime = min(datetime_dict.values())

    if return_all:
        return [key for key, value in datetime_dict.items() if value == min_datetime]
    else:
        # Return first key found with minimum value
        return next(
            key for key, value in datetime_dict.items() if value == min_datetime
        )


class PortfolioManager:
    """
    A thread-safe singleton class to manage the portfolio of assets.
    Supports both synchronous and asynchronous data loading.
    """

    _instance = None
    _lock = asyncio.Lock()

    def __init__(self, api_key: str, api_secret: str, saved_data: bool = False):
        if not hasattr(self, "_initialized"):
            self._saved_data = saved_data
            self._historical_data = HistoricalData(api_key, api_secret)
            self._symbol_attributes = ["units", "data", "close", "value", "weight"]

            # Initialize with default symbols
            self.symbols = {
                "BTCUSDT": {
                    "units": 1.0,
                    "data": pd.DataFrame(),
                    "close": 0.0,
                    "value": 0.0,
                    "weight": 0.0,
                    "colour": "#FF6B6B",
                },
                "ETHUSDT": {
                    "units": 1.0,
                    "data": pd.DataFrame(),
                    "close": 0.0,
                    "value": 0.0,
                    "weight": 0.0,
                    "colour": "#4ECDC4",
                },
                "SOLUSDC": {
                    "units": 1.0,
                    "data": pd.DataFrame(),
                    "close": 0.0,
                    "value": 0.0,
                    "weight": 0.0,
                    "colour": "#45B7D1",
                },
            }

            self._last_loaded = {
                symbol: dt.datetime.now() for symbol in self.symbols.keys()
            }
            self.portfolio_value = 0.0
            self.combined_data = None
            self.portfolio_performance = None
            self._initialized = True

    def __new__(cls, api_key: str, api_secret: str, saved_data: bool = False):
        if cls._instance is None:
            cls._instance = super(PortfolioManager, cls).__new__(cls)
        return cls._instance

    @classmethod
    async def create_async(
        cls, api_key: str, api_secret: str, saved_data: bool = False
    ):
        """Async factory method to create and initialize PortfolioManager"""
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls(api_key, api_secret, saved_data)
                await cls._instance.update_all_symbols_async(interval="1h")
            return cls._instance

    def get_symbol_list(self) -> List[str]:
        """Get list of all symbols in the portfolio"""
        return list(self.symbols.keys())

    def add_symbol(self, symbol: str, units: float = 1.0, interval: str = "1m") -> None:
        """Add a new symbol to the portfolio (synchronous)"""
        symbol = symbol.upper()
        if symbol not in self.symbols:
            self.symbols[symbol] = {
                attr: 0.0 if attr != "data" else pd.DataFrame()
                for attr in self._symbol_attributes
            }
            self.symbols[symbol]["units"] = units
            self.symbols[symbol]["data"] = self._historical_data.get_kline(
                symbol, interval
            )
            self.symbols[symbol]["close"] = (
                self.symbols[symbol]["data"]["close"].iloc[-1]
                if not self.symbols[symbol]["data"].empty
                else 0.0
            )
            self.symbols[symbol]["value"] = self.symbols[symbol]["close"] * units
            self.symbols[symbol]["colour"] = get_random_color()
            self._last_loaded[symbol] = dt.datetime.now()
            self._calculate_weighting()
        else:
            data_management_logger.info(
                f"Symbol {symbol} already exists in symbols dictionary."
            )

    async def add_symbol_async(
        self, symbol: str, units: float = 1.0, interval: str = "1m"
    ) -> None:
        """Add a new symbol to the portfolio (asynchronous)"""
        symbol = symbol.upper()
        if symbol not in self.symbols:
            self.symbols[symbol] = {
                attr: 0.0 if attr != "data" else pd.DataFrame()
                for attr in self._symbol_attributes
            }
            self.symbols[symbol]["units"] = units
            self.symbols[symbol]["data"] = await self._historical_data.get_kline_async(
                symbol, interval
            )
            self.symbols[symbol]["close"] = (
                self.symbols[symbol]["data"]["close"].iloc[-1]
                if not self.symbols[symbol]["data"].empty
                else 0.0
            )
            self.symbols[symbol]["value"] = self.symbols[symbol]["close"] * units
            self.symbols[symbol]["colour"] = get_random_color()
            self._last_loaded[symbol] = dt.datetime.now()
            self._calculate_weighting()
        else:
            data_management_logger.info(
                f"Symbol {symbol} already exists in symbols dictionary."
            )

    def remove_symbol(self, symbol: str) -> None:
        """Remove a symbol from the portfolio"""
        if symbol in self.symbols:
            del self.symbols[symbol]
            if symbol in self._last_loaded:
                del self._last_loaded[symbol]
            self._calculate_weighting()
            self._invalidate_computed_data()
        else:
            data_management_logger.warning(
                f"Symbol {symbol} not found in symbols dictionary."
            )

    def update_symbol(
        self, symbol: str, units: Optional[float] = None, interval: str = "1h"
    ) -> None:
        """Update a symbol's data (synchronous)"""
        if symbol not in self.symbols:
            raise ValueError(f"Symbol {symbol} not found in symbols dictionary.")

        if units is not None:
            self.symbols[symbol]["units"] = units

        self.symbols[symbol]["data"] = self._historical_data.get_kline(symbol, interval)
        self.symbols[symbol]["close"] = (
            self.symbols[symbol]["data"]["close"].iloc[-1]
            if not self.symbols[symbol]["data"].empty
            else 0.0
        )
        self.symbols[symbol]["value"] = (
            self.symbols[symbol]["close"] * self.symbols[symbol]["units"]
        )
        self._last_loaded[symbol] = dt.datetime.now()
        self._calculate_weighting()
        self._invalidate_computed_data()

    async def update_symbol_async(
        self, symbol: str, units: Optional[float] = None, update_data:bool = False, interval: str = "1h"
    ) -> None:
        """Update a symbol's data (asynchronous)"""
        if symbol not in self.symbols:
            raise ValueError(f"Symbol {symbol} not found in symbols dictionary.")

        if units is not None:
            self.symbols[symbol]["units"] = units

        if update_data:
            self.symbols[symbol]["data"] = await self._historical_data.get_kline_async(
                symbol, interval
            )
        
        self.symbols[symbol]["close"] = (
            self.symbols[symbol]["data"]["close"].iloc[-1]
            if not self.symbols[symbol]["data"].empty
            else 0.0
        )
        self.symbols[symbol]["value"] = (
            self.symbols[symbol]["close"] * self.symbols[symbol]["units"]
        )
        self._last_loaded[symbol] = dt.datetime.now()
        self._calculate_weighting()
        self._invalidate_computed_data()

    def update_all_symbols(
        self, units: Optional[float] = None, interval: str = "1h"
    ) -> None:
        """Update all symbols (synchronous)"""
        for symbol in self.symbols.keys():
            self.update_symbol(symbol, units, interval)

    async def update_all_symbols_async(
        self, units: Optional[float] = None, update_data:bool = False, interval: str = "1h"
    ) -> None:
        """Update all symbols concurrently (asynchronous)"""
        tasks = []
        for symbol in self.symbols.keys():
            task = self.update_symbol_async(symbol, units, update_data, interval)
            tasks.append(task)

        await asyncio.gather(*tasks, return_exceptions=True)

    def update_symbol_element(self, symbol: str, element: str, value: float) -> None:
        """Update a specific element of a symbol"""
        if symbol not in self.symbols:
            raise ValueError(f"Symbol {symbol} not found in symbols dictionary.")

        if element not in self._symbol_attributes:
            raise ValueError(f"Element {element} not found in symbol attributes.")

        self.symbols[symbol][element] = value
        if element in ["units", "close"]:
            self.symbols[symbol]["value"] = (
                self.symbols[symbol]["close"] * self.symbols[symbol]["units"]
            )
            self._calculate_weighting()

    def get_symbol_element(
        self, symbol: str, element: str
    ) -> Union[float, pd.DataFrame]:
        """Get a specific element of a symbol"""
        if symbol not in self.symbols:
            raise ValueError(f"Symbol {symbol} not found in symbols dictionary.")

        if element not in self.symbols[symbol]:
            raise ValueError(f"Element {element} not found in symbol {symbol}.")

        return self.symbols[symbol][element]

    def _calculate_weighting(self) -> None:
        """Calculate portfolio value and symbol weights"""
        self.portfolio_value = sum(
            self.symbols[symbol]["value"] for symbol in self.symbols.keys()
        )

        if self.portfolio_value > 0:
            for symbol in self.symbols.keys():
                self.symbols[symbol]["weight"] = (
                    self.symbols[symbol]["value"] / self.portfolio_value
                )
        else:
            for symbol in self.symbols.keys():
                self.symbols[symbol]["weight"] = 0.0

    def _invalidate_computed_data(self) -> None:
        """Invalidate cached computed data"""
        self.combined_data = None
        self.portfolio_performance = None

    def gen_combine_ohlc(self) -> None:
        """Generate combined OHLC data for all symbols"""
        if not self.symbols:
            self.combined_data = pd.DataFrame()
            return

        col_lst = ["open", "high", "low", "close", "volume", "log_returns"]
        dfs = []

        for symbol in self.get_symbol_list():
            data = self.symbols[symbol]["data"]
            if not data.empty:
                renamed_data = data.copy()
                for col in col_lst:
                    if col in renamed_data.columns:
                        renamed_data = renamed_data.rename(
                            columns={col: f"{col}_{symbol}"}
                        )
                dfs.append(renamed_data)

        if dfs:
            try:
                self.combined_data = reduce(
                    lambda left, right: pd.merge(
                        left, right, on=["closetime", "opentime"], how="outer"
                    ),
                    dfs,
                )
            except Exception as e:
                data_management_logger.error(f"Error combining OHLC data: {e}")
                self.combined_data = pd.DataFrame()
        else:
            self.combined_data = pd.DataFrame()

    def get_combined_ohlc(self) -> pd.DataFrame:
        """Get combined OHLC data for all symbols"""
        if self.combined_data is None:
            self.gen_combine_ohlc()
        return self.combined_data

    def gen_portfolio_performance(self) -> None:
        """Generate portfolio performance data"""
        if self.combined_data is None or self.combined_data.empty:
            self.portfolio_performance = pd.DataFrame()

        close_cols = [f"close_{symbol}" for symbol in self.get_symbol_list()]
        units = [self.symbols[symbol]["units"] for symbol in self.get_symbol_list()]

        # Filter out columns that don't exist
        existing_close_cols = [
            col for col in close_cols if col in self.combined_data.columns
        ]
        existing_units = [
            units[i]
            for i, col in enumerate(close_cols)
            if col in self.combined_data.columns
        ]

        if existing_close_cols and existing_units:
            result = pd.DataFrame()
            result["opentime"] = self.combined_data["opentime"]
            result["portfolio_value"] = np.dot(
                self.combined_data[existing_close_cols].fillna(0), existing_units
            )
            self.portfolio_performance = result
        else:
            self.portfolio_performance = pd.DataFrame()

    def get_portfolio_performance(self) -> pd.DataFrame:
        """Get portfolio performance data"""
        if self.portfolio_performance is None:
            self.gen_portfolio_performance()
        return self.portfolio_performance

    def get_portfolio_summary(self) -> Dict:
        """Get a summary of the portfolio"""
        return {
            "total_value": self.portfolio_value,
            "symbols": {
                symbol: {
                    "units": data["units"],
                    "close": data["close"],
                    "value": data["value"],
                    "weight": data["weight"],
                }
                for symbol, data in self.symbols.items()
            },
            "last_updated": max(self._last_loaded.values())
            if self._last_loaded
            else None,
        }


# Load configuration and initialize DataManager
config = parse_json("config.json")
portfolio_manager = PortfolioManager(
    api_key=config["binance"]["api_key".upper()],
    api_secret=config["binance"]["api_secret".upper()],
    saved_data=False,
)
asyncio.run(portfolio_manager.update_all_symbols_async(update_data = True))
portfolio_manager.gen_combine_ohlc()
portfolio_manager.gen_portfolio_performance()
