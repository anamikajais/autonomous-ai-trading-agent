import os

target_dir = os.path.join(os.path.expanduser("~"), "Downloads", "ai_trading_agent")

# 1. Vector Memory RAG Agent
memory_rag_code = """import logging
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
        \"\"\"Simulates vector similarity search over trade history lessons.\"\"\"
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
"""

# 2. Strategy Agent
strategy_code = """import logging
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
        macd = indicators.macd
        macd_sig = indicators.macd_signal

        if rsi is None:
            return

        query_context = f"RSI {rsi} MACD {macd}"
        retrieved_lessons = self.memory.retrieve_lessons(query_context)

        signal = None

        # Strategy Logic: Oversold Buy Signal
        if rsi < 40 or (macd is not None and macd_sig is not None and macd > macd_sig):
            confidence = 0.80 if rsi < 30 else 0.65
            rationale = f"Technical setup bullish (RSI: {rsi}). Memory Context: {retrieved_lessons[0]}"
            signal = Signal(
                timestamp=indicators.timestamp,
                symbol=indicators.symbol,
                side=OrderSide.BUY,
                confidence=confidence,
                proposed_quantity=50.0,
                rationale=rationale,
                retrieved_memory_lessons=retrieved_lessons
            )

        # Strategy Logic: Overbought Sell Signal
        elif rsi > 70:
            confidence = 0.85
            rationale = f"Technical setup overbought (RSI: {rsi}). Memory Context: {retrieved_lessons[0]}"
            signal = Signal(
                timestamp=indicators.timestamp,
                symbol=indicators.symbol,
                side=OrderSide.SELL,
                confidence=confidence,
                proposed_quantity=50.0,
                rationale=rationale,
                retrieved_memory_lessons=retrieved_lessons
            )

        if signal:
            print(f"[Strategy Agent] Emitted Signal: {signal.side} {signal.proposed_quantity} {signal.symbol} (Confidence: {signal.confidence*100:.0f}%) | Rationale: {signal.rationale[:60]}...")
            await self.bus.publish(signal)
"""

# 3. Mock Broker Execution Agent
mock_broker_code = """import logging
from datetime import datetime
from core.event_bus import EventBus
from core.models import Order, OrderStatus, FillReceipt, PortfolioState

logger = logging.getLogger(__name__)

class MockBroker:
    def __init__(self, event_bus: EventBus, portfolio: PortfolioState, slippage_pct: float = 0.0005, commission_per_trade: float = 1.0):
        self.bus = event_bus
        self.portfolio = portfolio
        self.slippage_pct = slippage_pct
        self.commission = commission_per_trade

    async def execute_order(self, order: Order) -> FillReceipt:
        if order.status != OrderStatus.APPROVED or order.quantity <= 0:
            return None

        # Apply simulated slippage physics
        if order.side == "BUY":
            fill_price = round(order.requested_price * (1.0 + self.slippage_pct), 2)
            total_cost = (fill_price * order.quantity) + self.commission
            
            self.portfolio.cash_balance -= total_cost
            current_qty = self.portfolio.positions.get(order.symbol, 0.0)
            self.portfolio.positions[order.symbol] = current_qty + order.quantity
            self.portfolio.cost_basis[order.symbol] = fill_price
        else:
            fill_price = round(order.requested_price * (1.0 - self.slippage_pct), 2)
            total_revenue = (fill_price * order.quantity) - self.commission
            
            self.portfolio.cash_balance += total_revenue
            current_qty = self.portfolio.positions.get(order.symbol, 0.0)
            self.portfolio.positions[order.symbol] = max(0.0, current_qty - order.quantity)

        # Update total portfolio valuation
        position_value = sum(qty * fill_price for qty in self.portfolio.positions.values())
        self.portfolio.total_portfolio_value = self.portfolio.cash_balance + position_value

        receipt = FillReceipt(
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            fill_price=fill_price,
            slippage=round(fill_price - order.requested_price, 4),
            commission=self.commission,
            timestamp=datetime.now()
        )

        print(f"[Mock Broker FILLED] {receipt.side} {receipt.quantity} {receipt.symbol} @ ${receipt.fill_price} | Cash Balance: ${self.portfolio.cash_balance:,.2f} | Total Value: ${self.portfolio.total_portfolio_value:,.2f}")
        await self.bus.publish(receipt)
        return receipt
"""

# 4. Integrated E2E Application Main loop
main_code = """import asyncio
from datetime import datetime
from core.event_bus import EventBus
from core.models import MarketBar, IndicatorVector, Signal, Order, PortfolioState
from agents.market_sim import MarketSimulator
from agents.analyst import TechnicalAnalyst
from agents.risk_manager import RiskManager
from agents.memory_rag import MemoryRAGAgent
from agents.strategy import StrategyAgent
from execution.mock_broker import MockBroker

async def main():
    bus = EventBus()

    # Initial Portfolio Balance: $100,000
    portfolio = PortfolioState(
        timestamp=datetime.now(),
        cash_balance=100000.0,
        positions={},
        cost_basis={},
        unrealized_pnl=0.0,
        realized_pnl=0.0,
        total_portfolio_value=100000.0
    )

    # Initialize Modules
    memory_agent = MemoryRAGAgent()
    market_sim = MarketSimulator(event_bus=bus, symbol="AAPL", initial_price=180.0)
    analyst = TechnicalAnalyst(event_bus=bus, min_history=15)
    strategy_agent = StrategyAgent(event_bus=bus, memory_rag=memory_agent)
    risk_manager = RiskManager(event_bus=bus, max_daily_drawdown_pct=0.02, min_cash_buffer_pct=0.10)
    broker = MockBroker(event_bus=bus, portfolio=portfolio)

    current_market_price = 180.0

    # Wire Event Bus Subscriptions across the pipeline
    async def on_market_bar(bar: MarketBar):
        nonlocal current_market_price
        current_market_price = bar.close
        await analyst.handle_market_bar(bar)

    async def on_indicators(indicators: IndicatorVector):
        await strategy_agent.handle_indicators(indicators)

    async def on_signal(signal: Signal):
        approved_order = await risk_manager.evaluate_signal(signal, portfolio, current_price=current_market_price)
        if approved_order and approved_order.status == "APPROVED":
            await broker.execute_order(approved_order)

    bus.subscribe(MarketBar, on_market_bar)
    bus.subscribe(IndicatorVector, on_indicators)
    bus.subscribe(Signal, on_signal)

    print("=========================================================================")
    print("      AUTONOMOUS AI TRADING AGENT SYSTEM RUNNING (CLOSED-LOOP)           ")
    print("=========================================================================\\n")

    # Run 25 bar market loop
    await market_sim.start_streaming(interval_seconds=0.05, total_bars=25)

    print("\\n=========================================================================")
    print("                        FINAL PORTFOLIO SUMMARY                          ")
    print("=========================================================================")
    print(f" Cash Balance:            ${portfolio.cash_balance:,.2f}")
    print(f" Open Positions:          {portfolio.positions}")
    print(f" Total Portfolio Value:   ${portfolio.total_portfolio_value:,.2f}")
    print("=========================================================================")

if __name__ == "__main__":
    asyncio.run(main())
"""

files = {
    "agents/memory_rag.py": memory_rag_code,
    "agents/strategy.py": strategy_code,
    "execution/mock_broker.py": mock_broker_code,
    "main.py": main_code
}

for rel_path, content in files.items():
    full_path = os.path.join(target_dir, rel_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

print("Phase 4 & 5 code successfully generated!")