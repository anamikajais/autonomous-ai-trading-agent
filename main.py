import asyncio
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
    print("=========================================================================\n")

    # Run 25 bar market loop
    await market_sim.start_streaming(interval_seconds=0.05, total_bars=25)

    print("\n=========================================================================")
    print("                        FINAL PORTFOLIO SUMMARY                          ")
    print("=========================================================================")
    print(f" Cash Balance:            ${portfolio.cash_balance:,.2f}")
    print(f" Open Positions:          {portfolio.positions}")
    print(f" Total Portfolio Value:   ${portfolio.total_portfolio_value:,.2f}")
    print("=========================================================================")

if __name__ == "__main__":
    asyncio.run(main())
