import logging
import uuid
from datetime import datetime
from core.event_bus import EventBus
from core.models import Signal, Order, OrderStatus, OrderSide, PortfolioState

logger = logging.getLogger(__name__)

class RiskManager:
    def __init__(
        self,
        event_bus: EventBus,
        max_daily_drawdown_pct: float = 0.02,  # 2% max daily portfolio loss
        min_cash_buffer_pct: float = 0.10,     # 10% mandatory unallocated liquid cash buffer
        max_position_pct: float = 0.10,        # 10% max allocation per single asset
        reward_risk_ratio: float = 1.5         # Default R:R ratio assumption
    ):
        self.bus = event_bus
        self.max_daily_drawdown_pct = max_daily_drawdown_pct
        self.min_cash_buffer_pct = min_cash_buffer_pct
        self.max_position_pct = max_position_pct
        self.reward_risk_ratio = reward_risk_ratio
        self.circuit_breaker_triggered = False

    def calculate_kelly_fraction(self, win_rate: float) -> float:
        """
        Calculates Fractional Kelly Criterion (Half-Kelly).
        Formula: f* = w - ((1 - w) / R)
        Half-Kelly = 0.5 * f*
        """
        w = max(0.01, min(0.99, win_rate))
        r = self.reward_risk_ratio
        full_kelly = w - ((1.0 - w) / r)
        half_kelly = max(0.0, full_kelly * 0.5)
        return half_kelly

    async def evaluate_signal(self, signal: Signal, portfolio: PortfolioState, current_price: float) -> Order:
        order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"

        # 1. Circuit Breaker Check
        if self.circuit_breaker_triggered:
            print(f"[Risk Manager] REJECTED: Daily Circuit Breaker is ACTIVE.")
            return Order(
                order_id=order_id,
                symbol=signal.symbol,
                side=signal.side,
                quantity=0.0,
                requested_price=current_price,
                status=OrderStatus.REJECTED,
                rejection_reason="REJECTED: Daily Loss Circuit Breaker active."
            )

        total_pnl = portfolio.realized_pnl + portfolio.unrealized_pnl
        if total_pnl < -(self.max_daily_drawdown_pct * portfolio.total_portfolio_value):
            self.circuit_breaker_triggered = True
            print(f"[Risk Manager] 🚨 CIRCUIT BREAKER TRIGGERED! PnL Loss: ${total_pnl:.2f}")
            return Order(
                order_id=order_id,
                symbol=signal.symbol,
                side=signal.side,
                quantity=0.0,
                requested_price=current_price,
                status=OrderStatus.REJECTED,
                rejection_reason=f"REJECTED: Daily drawdown limit ({self.max_daily_drawdown_pct*100}%) breached."
            )

        # Handle SELL signals
        if signal.side == OrderSide.SELL:
            current_qty = portfolio.positions.get(signal.symbol, 0.0)
            if current_qty <= 0:
                print(f"[Risk Manager] REJECTED: Cannot sell {signal.symbol} (0 units owned).")
                return Order(
                    order_id=order_id,
                    symbol=signal.symbol,
                    side=signal.side,
                    quantity=0.0,
                    requested_price=current_price,
                    status=OrderStatus.REJECTED,
                    rejection_reason="REJECTED: Cannot sell non-existent position."
                )
            exec_qty = min(signal.proposed_quantity, current_qty)
            approved_order = Order(
                order_id=order_id,
                symbol=signal.symbol,
                side=signal.side,
                quantity=exec_qty,
                requested_price=current_price,
                status=OrderStatus.APPROVED,
                risk_approval_reason=f"APPROVED: Sell order for {exec_qty} units."
            )
            await self.bus.publish(approved_order)
            return approved_order

        # 2. Kelly Criterion Sizing & Cash Cushion Verification (BUY signals)
        kelly_frac = self.calculate_kelly_fraction(signal.confidence)
        allowed_position_frac = min(kelly_frac, self.max_position_pct)
        max_allowed_dollar_amt = portfolio.total_portfolio_value * allowed_position_frac

        min_cash_required = portfolio.total_portfolio_value * self.min_cash_buffer_pct
        available_cash_for_trading = max(0.0, portfolio.cash_balance - min_cash_required)

        trade_budget = min(max_allowed_dollar_amt, available_cash_for_trading)
        max_buy_qty = trade_budget / current_price if current_price > 0 else 0.0

        final_qty = min(signal.proposed_quantity, max_buy_qty)

        if final_qty <= 0.01:
            print(f"[Risk Manager] REJECTED: Insufficient unallocated cash or position cap reached.")
            return Order(
                order_id=order_id,
                symbol=signal.symbol,
                side=signal.side,
                quantity=0.0,
                requested_price=current_price,
                status=OrderStatus.REJECTED,
                rejection_reason="REJECTED: Insufficient unallocated cash buffer or position cap reached."
            )

        approved_order = Order(
            order_id=order_id,
            symbol=signal.symbol,
            side=signal.side,
            quantity=round(final_qty, 2),
            requested_price=current_price,
            status=OrderStatus.APPROVED,
            risk_approval_reason=f"APPROVED (Half-Kelly: {kelly_frac:.2%}, Qty resized from {signal.proposed_quantity} -> {round(final_qty, 2)})"
        )

        print(f"[Risk Manager ORDER APPROVED] {approved_order.side} {approved_order.quantity} x {approved_order.symbol} @ ${approved_order.requested_price} | {approved_order.risk_approval_reason}")
        await self.bus.publish(approved_order)
        return approved_order
