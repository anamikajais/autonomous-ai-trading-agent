import logging
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
