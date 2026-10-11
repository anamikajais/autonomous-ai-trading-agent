import asyncio
import random
from datetime import datetime, timedelta
from core.event_bus import EventBus
from core.models import MarketBar

class MarketSimulator:
    def __init__(self, event_bus: EventBus, symbol: str = "AAPL", initial_price: float = 180.0):
        self.bus = event_bus
        self.symbol = symbol
        self.current_price = initial_price
        self.running = False

    async def start_streaming(self, interval_seconds: float = 0.2, total_bars: int = 20):
        self.running = True
        curr_time = datetime.now()
        for _ in range(total_bars):
            if not self.running:
                break
            change_pct = random.uniform(-0.015, 0.015)
            open_p = self.current_price
            close_p = open_p * (1 + change_pct)
            high_p = max(open_p, close_p) * (1 + random.uniform(0.001, 0.005))
            low_p = min(open_p, close_p) * (1 - random.uniform(0.001, 0.005))
            volume = float(random.randint(10000, 50000))
            
            bar = MarketBar(
                timestamp=curr_time,
                symbol=self.symbol,
                open=round(open_p, 2),
                high=round(high_p, 2),
                low=round(low_p, 2),
                close=round(close_p, 2),
                volume=volume
            )
            self.current_price = close_p
            curr_time += timedelta(minutes=1)
            await self.bus.publish(bar)
            await asyncio.sleep(interval_seconds)
