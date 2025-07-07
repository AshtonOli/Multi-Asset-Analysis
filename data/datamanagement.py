import pandas as pd
import datetime as dt
from data.binance_connector import HistoricalData
from src.util import parse_json
class DataManager:
    _instance = None
    _last_loaded = {}
    __api_key = None
    __api_secret = None
    _saved_data = False
    _historical_data = HistoricalData
    symbols = {
        "BTCUSDT": {"units" : 1.0, "data" : pd.DataFrame,"close" : 0.0, "value": 0.0, "weight": 0.0},
        "ETHUSDT": {"units" : 1.0, "data" : pd.DataFrame,"close" : 0.0, "value": 0.0, "weight": 0.0},
        "SOLUSDC": {"units" : 1.0, "data" : pd.DataFrame,"close" : 0.0, "value": 0.0, "weight": 0.0},
    }

    def __new__(cls,api_key: str, api_secret: str, saved_data: bool = False):

        if cls._instance is None:
            cls._instance = super(DataManager, cls).__new__(cls)
            cls._instance.__api_key = api_key
            cls._instance.__api_secret = api_secret
            cls._instance._saved_data = saved_data
            cls._instance._historical_data = HistoricalData(api_key, api_secret)
            cls._instance._last_loaded = {symbol: dt.datetime.now() for symbol in cls._instance.symbols.keys()}
            cls._instance.update_symbol_data(list(cls._instance.symbols.keys()), "1m")
        return cls._instance
    
    def get_symbol_list(self) -> list:
        return list(self.symbols.keys())

    def _load_data(self, symbol: str, interval: str, force_load: bool = False) -> pd.DataFrame:

        if symbol not in self.symbols or (dt.datetime.now() - self._last_loaded[symbol]) > dt.timedelta(minutes=5) or force_load:
            print("loading data for symbol", symbol)
            df = self._historical_data.getKline(symbol, interval)
            self._last_loaded[symbol] = dt.datetime.now()
            self.symbols[symbol] = {"units": 1, "data": df}
        else:
            df : pd.DataFrame = self.symbols[symbol]["data"]
            if df.empty:
                print("loading data for symbol", symbol)
                df = self._historical_data.getKline(symbol, interval)
                self._last_loaded[symbol] = dt.datetime.now()
                self.symbols[symbol]["data"] = df

    def add_symbol(self, symbol: str, units: float = 1) -> None:
        if symbol not in self.symbols:
            self.symbols[symbol] = {"units": units, "data": self._load_data(symbol, "1m")}
        else:
            print(f"Symbol {symbol} already exists in symbols dictionary.")
    
    def remove_symbol(self, symbol: str) -> None:
        if symbol in self.symbols:
            del self.symbols[symbol]
        else:
            print(f"Symbol {symbol} not found in symbols dictionary.")

    def update_symbol_data(self, symbols: str | list, interval: str = "1m") -> pd.DataFrame:
        if isinstance(symbols, str):
            symbols = [symbols]
        for symbol in symbols:
            if symbol in self.symbols:
                self._load_data(symbol, interval,True)

            else:
                raise ValueError(f"Symbol {symbol} not found in symbols dictionary.")

    def update_symbol_element(self, symbol: str, element: str, value: float) -> None:
        if symbol in self.symbols:
            if element in self.symbols[symbol]:
                if element == "data":
                    self.update_symbol_data(symbol, "1m")
                else:
                    self.symbols[symbol][element] = value
            else:
                raise ValueError(f"Element {element} not found in symbol {symbol}.")
        else:
            raise ValueError(f"Symbol {symbol} not found in symbols dictionary.")
    
    def get_symbol_element(self, symbol: str, element: str) -> float:
        if symbol in self.symbols:
            if element in self.symbols[symbol]:
                return self.symbols[symbol][element]
            else:
                raise ValueError(f"Element {element} not found in symbol {symbol}.")
        else:
            raise ValueError(f"Symbol {symbol} not found in symbols dictionary.")

# Load configuration and initialize DataManager      
config = parse_json("config.json")
data_manager = DataManager(
    api_key=config["binance"]["api_key".upper()],
    api_secret=config["binance"]["api_secret".upper()],
    saved_data=False
)

class PortfolioManager():
    """
    A class to manage the portfolio of assets.
    It will be used to calculate the total value, weight, and other metrics of the portfolio.
    """
    _instance = None
    _last_loaded = {}
    __api_key = None
    __api_secret = None
    _saved_data = False
    _historical_data = HistoricalData
    _symbol_attributes = ["units", "data", "close", "value", "weight"]
    symbols = {
        "BTCUSDT": {"units" : 1.0, "data" : pd.DataFrame(),"close" : 0.0, "value": 0.0, "weight": 0.0},
        "ETHUSDT": {"units" : 1.0, "data" : pd.DataFrame(),"close" : 0.0, "value": 0.0, "weight": 0.0},
        "SOLUSDC": {"units" : 1.0, "data" : pd.DataFrame(),"close" : 0.0, "value": 0.0, "weight": 0.0},
    }

    def __new__(cls,api_key: str, api_secret: str, saved_data: bool = False):
        if cls._instance is None:
            cls._instance = super(PortfolioManager, cls).__new__(cls)
            cls._instance.__api_key = api_key
            cls._instance.__api_secret = api_secret
            cls._instance._saved_data = saved_data
            cls._instance._historical_data = HistoricalData(api_key, api_secret)
            cls._instance._last_loaded = {symbol: dt.datetime.now() for symbol in cls._instance.symbols.keys()}
        return cls._instance
    
    def get_symbol_list(self) -> list:
        return list(self.symbols.keys())
    
    def add_symbol(self, symbol: str, units: float = 1, interval: str = "1m") -> None:
        if symbol not in self.symbols:
            self.symbols[symbol] = {attr: 0 for attr in self._symbol_attributes}
            self.symbols[symbol]["units"] = units
            self.symbols[symbol]["data"] = self._historical_data.getKline(symbol, interval)
            self.symbols[symbol]["close"] = self.symbols[symbol]["data"].iloc[-1] if not self.symbols[symbol]["data"].empty else 0.0
            self.symbols[symbol]["value"] = self.symbols[symbol]["close"] * units
            self.symbols[symbol]["weight"] = 0.0  # Placeholder for weight
        else:
            print(f"Symbol {symbol} already exists in symbols dictionary.")
    
    def remove_symbol(self, symbol: str) -> None:
        if symbol in self.symbols:
            del self.symbols[symbol]
        else:
            print(f"Symbol {symbol} not found in symbols dictionary.")

    def update_symbol(self, symbol: str, units: float = 1.0, interval: str | None = None) -> None:
        if symbol in self.symbols:
            self.symbols[symbol]["units"] = units
            self.symbols[symbol]["data"] = self._historical_data.getKline(symbol, interval)
            self.symbols[symbol]["close"] = self.symbols[symbol]["data"].iloc[-1] if not self.symbols[symbol]["data"].empty else 0.0
            self.symbols[symbol]["value"] = self.symbols[symbol]["close"] * units
        else:
            raise ValueError(f"Symbol {symbol} not found in symbols dictionary.")
    
    def update_symbol_element(self, symbol: str, element: str, value: float) -> None:
        if symbol in self.symbols:
            if element in self._symbol_attributes:
                self.symbols[symbol][element] = value
            else:
                raise ValueError(f"Element {element} not found in symbol {symbol}.")
        else:
            raise ValueError(f"Symbol {symbol} not found in symbols dictionary.")

    
