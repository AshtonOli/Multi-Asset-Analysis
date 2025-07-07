import pandas as pd
from binance import Client
import numpy as np
class HistoricalData:
    data = None
    intervals = {
        "1s":Client.KLINE_INTERVAL_1SECOND,
        "1m": Client.KLINE_INTERVAL_1MINUTE,
        "1d": Client.KLINE_INTERVAL_1DAY,
        "1M": Client.KLINE_INTERVAL_1MONTH,
        "12h": Client.KLINE_INTERVAL_12HOUR,
        "1h": Client.KLINE_INTERVAL_1HOUR,
        }

    def __init__(self, api_key: str, api_secret: str) -> None:
        self.client = Client(api_key, api_secret)

    def getKline(self, symbol: str, interval: str):
        try:
            data = self.client.get_historical_klines(symbol, self.intervals[interval])
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
                    "volume",
                    "ntrades",
                    "Taker buy base asset volume",
                    "Taker buy quote asset volume",
                    "Ignore",
                ],
            )
            df["opentime"] = pd.to_datetime(df.opentime, unit="ms")
            df["closetime"] = pd.to_datetime(df.closetime, unit="ms")
            df["open"] = df.open.astype(float)
            df["high"] = df.high.astype(float)
            df["low"] = df.low.astype(float)
            df["close"] = df.close.astype(float)
            df["volume"] = df.volume.astype(float)
            df["log_returns"] = np.log(df["close"]/df["close"].shift(1))
            df = df.drop([
                "ntrades",
                "Taker buy base asset volume",
                "Taker buy quote asset volume",
                "Ignore",
            ],axis = 1)
        except Exception as e:
            print(f"Error fetching data for {symbol} with interval {interval}: {e}")
            return pd.DataFrame()
        self.data = df
        return df

    def save_data(self, path: str) -> None:
        self.data.to_csv(path,index=False)
