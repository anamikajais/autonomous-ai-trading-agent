from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"

class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"

class MarketBar(BaseModel):
    timestamp: datetime
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float

class IndicatorVector(BaseModel):
    timestamp: datetime
    symbol: str
    close_price: float
    rsi_14: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    ema_20: Optional[float] = None
    ema_50: Optional[float] = None
    atr_14: Optional[float] = None

class Signal(BaseModel):
    timestamp: datetime
    symbol: str
    side: OrderSide
    confidence: float = Field(ge=0.0, le=1.0)
    proposed_quantity: float
    rationale: str
    retrieved_memory_lessons: List[str] = []

class Order(BaseModel):
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType = OrderType.MARKET
    quantity: float
    requested_price: float
    status: OrderStatus = OrderStatus.PENDING
    risk_approval_reason: Optional[str] = None
    rejection_reason: Optional[str] = None

class FillReceipt(BaseModel):
    order_id: str
    symbol: str
    side: OrderSide
    quantity: float
    fill_price: float
    slippage: float
    commission: float
    timestamp: datetime

class PortfolioState(BaseModel):
    timestamp: datetime
    cash_balance: float
    positions: Dict[str, float]
    cost_basis: Dict[str, float]
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    total_portfolio_value: float
