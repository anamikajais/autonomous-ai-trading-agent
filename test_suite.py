import asyncio
import os
from datetime import datetime
from core.event_bus import EventBus
from core.models import MarketBar, IndicatorVector, Signal, OrderSide, OrderStatus, PortfolioState
from agents.risk_manager import RiskManager
from agents.strategy import StrategyAgent
from agents.memory_rag import MemoryRAGAgent
from execution.mock_broker import MockBroker

async def run_tests():
    print("=================================================================")
    print("           AUTONOMOUS TRADING AGENT ROBUSTNESS TEST SUITE         ")
    print("=================================================================\n")
    
    bus = EventBus()
    portfolio = PortfolioState(
        timestamp=datetime.now(),
        cash_balance=100000.0,
        positions={},
        cost_basis={},
        unrealized_pnl=0.0,
        realized_pnl=0.0,
        total_portfolio_value=100000.0
    )
    
    risk_mgr = RiskManager(event_bus=bus, max_daily_drawdown_pct=0.02, min_cash_buffer_pct=0.10)
    broker = MockBroker(event_bus=bus, portfolio=portfolio)
    memory = MemoryRAGAgent()
    strategy = StrategyAgent(event_bus=bus, memory_rag=memory)
    
    tests_passed = 0
    total_tests = 4

    # -----------------------------------------------------------------
    # TEST 1: Oversized Buy Signal (Anti-Hallucination / Cash Cushion Test)
    # -----------------------------------------------------------------
    print("[TEST 1] Testing Over-sized Trade Request (Strategy asks for 1,000,000 shares)...")
    huge_signal = Signal(
        timestamp=datetime.now(),
        symbol="AAPL",
        side=OrderSide.BUY,
        confidence=0.99,
        proposed_quantity=1000000.0,
        rationale="Hallucinated over-leveraged trade."
    )
    order1 = await risk_mgr.evaluate_signal(huge_signal, portfolio, current_price=180.0)
    
    # Capital is 100k, max single position cap is 10% (10k), price is 180 -> max ~55.5 shares
    if order1.status == OrderStatus.APPROVED and order1.quantity <= 60.0:
        print(f"  ✓ PASSED: Risk Manager safely resized order from 1,000,000 -> {order1.quantity} shares.\n")
        tests_passed += 1
    else:
        print(f"  ❌ FAILED: Order execution violated risk boundaries!\n")

    # -----------------------------------------------------------------
    # TEST 2: Illegal Short / Sell Test
    # -----------------------------------------------------------------
    print("[TEST 2] Testing Illegal Sell Signal (Owning 0 shares)...")
    illegal_sell_signal = Signal(
        timestamp=datetime.now(),
        symbol="AAPL",
        side=OrderSide.SELL,
        confidence=0.85,
        proposed_quantity=100.0,
        rationale="Attempting to sell non-existent position."
    )
    order2 = await risk_mgr.evaluate_signal(illegal_sell_signal, portfolio, current_price=180.0)
    
    if order2.status == OrderStatus.REJECTED:
        print(f"  ✓ PASSED: Risk Manager rejected illegal sell order. Reason: {order2.rejection_reason}\n")
        tests_passed += 1
    else:
        print(f"  ❌ FAILED: Approved sell order on non-existent position!\n")

    # -----------------------------------------------------------------
    # TEST 3: Daily Drawdown Circuit Breaker Trigger
    # -----------------------------------------------------------------
    print("[TEST 3] Testing Circuit Breaker on -5% Portfolio Drawdown...")
    damaged_portfolio = PortfolioState(
        timestamp=datetime.now(),
        cash_balance=95000.0,
        positions={},
        cost_basis={},
        unrealized_pnl=-5000.0,  # 5% drawdown (limit is 2%)
        realized_pnl=0.0,
        total_portfolio_value=95000.0
    )
    valid_signal = Signal(
        timestamp=datetime.now(),
        symbol="AAPL",
        side=OrderSide.BUY,
        confidence=0.80,
        proposed_quantity=10.0,
        rationale="Valid setup during severe market crash."
    )
    order3 = await risk_mgr.evaluate_signal(valid_signal, damaged_portfolio, current_price=180.0)
    
    if order3.status == OrderStatus.REJECTED and risk_mgr.circuit_breaker_triggered:
        print(f"  ✓ PASSED: Circuit breaker activated and blocked all incoming trades.\n")
        tests_passed += 1
    else:
        print(f"  ❌ FAILED: Circuit breaker failed to halt trading during severe loss!\n")

    # -----------------------------------------------------------------
    # TEST 4: Null / Corrupted Indicator Vector Handling
    # -----------------------------------------------------------------
    print("[TEST 4] Testing Corrupted Indicator Data Ingestion (None/NaN values)...")
    corrupted_vector = IndicatorVector(
        timestamp=datetime.now(),
        symbol="AAPL",
        close_price=180.0,
        rsi_14=None,  # Missing indicator data during warmup
        macd=None,
        macd_signal=None,
        ema_20=None,
        ema_50=None,
        atr_14=None
    )
    try:
        await strategy.handle_indicators(corrupted_vector)
        print("  ✓ PASSED: Strategy agent handled missing indicators gracefully without throwing errors.\n")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: System crashed on missing indicator data: {e}\n")

    print("=================================================================")
    print(f"              TEST RESULTS: {tests_passed}/{total_tests} PASSED")
    print("=================================================================")

if __name__ == "__main__":
    asyncio.run(run_tests())