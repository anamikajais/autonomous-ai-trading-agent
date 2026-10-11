import pandas as pd
import pandas_ta as ta
from core.event_bus import EventBus
from core.models import MarketBar, IndicatorVector

class TechnicalAnalyst:
    def __init__(self, event_bus: EventBus, min_history: int = 15):
        self.bus = event_bus
        self.min_history = min_history
        self.history = []

    async def handle_market_bar(self, bar: MarketBar):
        self.history.append({
            "timestamp": bar.timestamp,
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume
        })
        
        if len(self.history) < self.min_history:
            print(f"[Analyst] Warming up indicators ({len(self.history)}/{self.min_history} bars)...")
            return

        df = pd.DataFrame(self.history)
        df["rsi"] = ta.rsi(df["close"], length=14)
        macd_df = ta.macd(df["close"])
        if macd_df is not None:
            df["macd"] = macd_df["MACD_12_26_9"]
            df["macd_signal"] = macd_df["MACDs_12_26_9"]
        
        df["ema_20"] = ta.ema(df["close"], length=20)
        df["ema_50"] = ta.ema(df["close"], length=50)
        atr_df = ta.atr(df["high"], df["low"], df["close"], length=14)
        if atr_df is not None:
            df["atr"] = atr_df

        latest = df.iloc[-1]
        indicator_vector = IndicatorVector(
            timestamp=bar.timestamp,
            symbol=bar.symbol,
            close_price=bar.close,
            rsi_14=round(latest["rsi"], 2) if pd.notna(latest.get("rsi")) else None,
            macd=round(latest["macd"], 4) if pd.notna(latest.get("macd")) else None,
            macd_signal=round(latest["macd_signal"], 4) if pd.notna(latest.get("macd_signal")) else None,
            ema_20=round(latest["ema_20"], 2) if pd.notna(latest.get("ema_20")) else None,
            ema_50=round(latest["ema_50"], 2) if pd.notna(latest.get("ema_50")) else None,
            atr_14=round(latest["atr"], 2) if pd.notna(latest.get("atr")) else None
        )
        print(f"[Analyst Indicator Generated] {bar.symbol} Close: ${bar.close} | RSI: {indicator_vector.rsi_14} | MACD: {indicator_vector.macd}")
        await self.bus.publish(indicator_vector)
