# 🤖 Autonomous AI-Driven Multi-Agent Trading System

An event-driven quantitative trading framework built entirely in Python. The system orchestrates specialized autonomous agents—Market Data Simulator, Technical Analyst, RAG Memory Module, Strategy Generator, Risk Manager, and Mock Broker—to simulate real-world algorithmic trading physics without relying on third-party cloud API keys or external fees.

---

## 🎯 Key Features

* **Event-Driven Architecture:** Decoupled asynchronous messaging between agents via a central `EventBus` and strict Pydantic data validation schemas.
* **Offline-First & Deterministic:** Operates 100% locally using local technical analysis (`pandas-ta`) and vector memory retrieval.
* **Quantitative Risk Sizing:** Implements the **Half-Kelly Criterion** to dynamically size orders based on signal confidence and reward-to-risk expectations.
* **Strict Capital Guardrails:** Enforces a mandatory **10% liquid cash reserve** and an automated **2% daily drawdown circuit breaker**.
* **Market Friction Physics:** Simulates real-world order execution with fixed commissions and bid-ask price slippage ($0.05\%$).
* **Interactive Streamlit Dashboard:** Live monitoring of price candles, technical indicators, audit transaction logs, win rates, and total portfolio equity.

---

## 🏗️ System Architecture & Agent Workflow

1. **Market Simulator (`market_sim.py`):** Streams synthetic stock price ticks using Geometric Brownian Motion (GBM).
2. **Technical Analyst (`analyst.py`):** Computes rolling window indicators (RSI-14, MACD, EMA).
3. **Memory Agent (`memory_rag.py`):** Matches current market regimes against historical trade reflection logs.
4. **Strategy Agent (`strategy.py`):** Generates buy/sell trade signals based on technical conditions and memory context.
5. **Risk Manager (`risk_manager.py`):** Filters signals, applies Half-Kelly sizing, and enforces portfolio safety limits.
6. **Mock Broker (`mock_broker.py`):** Executes trades with realistic slippage and updates portfolio state in real time.

---

## 🚀 Quick Start

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/your-username/repository-name.git](https://github.com/your-username/repository-name.git)
   cd repository-name
