import logging
from datetime import datetime
from core.event_bus import EventBus
from core.models import IndicatorVector, Signal, OrderSide
from agents.memory_rag import MemoryRAGAgent

logger = logging.getLogger(__name__)

class StrategyAgent:
    def __init__(self, event_bus: EventBus, memory_rag: MemoryRAGAgent):
        self.bus = event_bus
        self.memory = memory_rag

    async def handle_indicators(self, indicators: IndicatorVector):
        rsi = indicators.rsi_14
        if rsi is None:
            return

        query_context = f"RSI {rsi}"
        retrieved_lessons = self.memory.retrieve_lessons(query_context)

        signal = None

        # Responsive thresholds for demonstration runs
        if rsi < 55:
            confidence = 0.75
            rationale = f"Bullish entry trigger (RSI: {rsi}). Memory: {retrieved_lessons[0]}"
            signal = Signal(
                timestamp=indicators.timestamp,
                symbol=indicators.symbol,
                side=OrderSide.BUY,
                confidence=confidence,
                proposed_quantity=40.0,
                rationale=rationale,
                retrieved_memory_lessons=retrieved_lessons
            )
        elif rsi > 65:
            confidence = 0.80
            rationale = f"Bearish exit trigger (RSI: {rsi}). Memory: {retrieved_lessons[0]}"
            signal = Signal(
                timestamp=indicators.timestamp,
                symbol=indicators.symbol,
                side=OrderSide.SELL,
                confidence=confidence,
                proposed_quantity=40.0,
                rationale=rationale,
                retrieved_memory_lessons=retrieved_lessons
            )

        if signal:
            print(f"[Strategy Agent] Emitted Signal: {signal.side} {signal.proposed_quantity} {signal.symbol}")
            await self.bus.publish(signal)
