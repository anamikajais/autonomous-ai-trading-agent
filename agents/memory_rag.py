import logging
from typing import List

logger = logging.getLogger(__name__)

class MemoryRAGAgent:
    def __init__(self, collection_name: str = "trade_lessons"):
        self.lessons = [
            {"condition": "RSI below 30 with bullish MACD", "lesson": "Strong rebound probability. High win-rate buy entry.", "pnl": 350.0},
            {"condition": "RSI above 70 overbought", "lesson": "High danger of sudden price drop. Avoid buying.", "pnl": -200.0},
            {"condition": "EMA 20 crossing below EMA 50", "lesson": "Bearish trend starting. Consider liquidating long positions.", "pnl": 150.0},
            {"condition": "High ATR volatility spike", "lesson": "Increase slippage tolerance and decrease position sizing.", "pnl": -80.0}
        ]

    def retrieve_lessons(self, current_context: str, top_k: int = 2) -> List[str]:
        """Simulates vector similarity search over trade history lessons."""
        relevant = []
        words = set(current_context.lower().split())
        for item in self.lessons:
            cond_words = set(item["condition"].lower().split())
            if words.intersection(cond_words):
                relevant.append(f"Lesson (Past PnL: ${item['pnl']:.2f}): {item['lesson']}")
        
        if not relevant:
            relevant.append("Default Memory: Maintain conservative position sizing and strict risk limits.")
        return relevant[:top_k]

    def record_reflection(self, context: str, lesson: str, realized_pnl: float):
        self.lessons.append({"condition": context, "lesson": lesson, "pnl": realized_pnl})
        print(f"[Memory Agent] Indexed new trade lesson into Vector DB! PnL: ${realized_pnl:.2f}")
