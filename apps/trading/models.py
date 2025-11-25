from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal

from apps.market.models import Asset, Currency
from apps.wallets.models import Transaction, Wallet
from apps.wallets import models
from config import settings

class OrderType(models.TextChoices):
    """
    Represents a buy or sell order placed by a user.
    
    Service Layer Responsibilities (in services.py):
    - Validate user has sufficient funds (BUY) or holdings (SELL)
    - Check market hours for stocks via Exchange model
    - Handle FX conversion when asset.currency != user's wallet.currency
    - Execute MARKET orders immediately at current price
    - Queue LIMIT orders and match when price conditions are met
    - Update order status and filled_quantity as trades execute
    - Cancel expired or user-requested cancellations
    """
        
    """Type of order execution."""
    MARKET = 'MARKET', 'Market Order'
    LIMIT = 'LIMIT', 'Limit Order'

class OrderSide(models.TextChoices):
    """Direction of the trade."""
    BUY = 'BUY', 'Buy'
    SELL = 'SELL', 'Sell'

class OrderStatus(models.TextChoices):
    """Current state of an order."""
    PENDING = 'PENDING', 'Pending'
    PARTIALLY_FILLED = 'PARTIALLY_FILLED', 'Partially Filled'
    FILLED = 'FILLED', 'Filled'
    CANCELLED = 'CANCELLED', 'Cancelled'
    REJECTED = 'REJECTED', 'Rejected'


class Order(models.Model):
    user = models.ForeignKey(
            settings.AUTH_USER_MODEL,
            on_delete=models.CASCADE,
            related_name='orders'
        )
    asset = models.ForeignKey(
        Asset,
        on_delete=models.PROTECT,
        related_name='orders'
    )
    order_type = models.CharField(
        max_length=10,
        choices=OrderType.choices,
        default=OrderType.MARKET
    )
    side = models.CharField(
        max_length=4,
        choices=OrderSide.choices
    )
    quantity = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        validators=[MinValueValidator(Decimal('0.00000001'))],
        help_text="Total quantity requested"
    )
    filled_quantity = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Quantity filled so far (for partial fills)"
    )
    limit_price = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00000001'))],
        help_text="Target price for LIMIT orders (in asset's currency)"
    )
    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['asset', 'status', 'order_type']),
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f"{self.get_side_display()} {self.quantity} {self.asset.symbol} - {self.get_status_display()}"

    @property
    def remaining_quantity(self) -> Decimal:
        """ unfilled portion of the order."""
        return self.quantity - self.filled_quantity

    @property
    def is_fully_filled(self) -> bool:
        return self.filled_quantity >= self.quantity

    @property
    def is_active(self) -> bool:
        """if order can still be executed"""
        return self.status in [OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED]

    @property
    def fill_percentage(self) -> Decimal:
        """how much of order has been filled"""
        if self.quantity == 0:
            return Decimal('0')
        return (self.filled_quantity / self.quantity) * 100
    


class Position(models.Model):
    """
    Tracks a user's current holdings in a specific asset.
    One position per user-asset pair.
    
    Service Layer Responsibilities (in services.py):
    - Create position on first BUY trade
    - On BUY: Update quantity and recalculate average_cost using weighted average
      Formula: new_avg = (current_qty * current_avg + trade_qty * trade_price) / (current_qty + trade_qty)
    - On SELL: Reduce quantity, keep average_cost same, calculate realized_pnl
      realized_pnl += (sell_price - average_cost) * sell_quantity - fees
    - Delete or mark inactive when quantity reaches zero
    - Fetch current price from PriceHistory for unrealized P&L calculations
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='positions'
    )
    asset = models.ForeignKey(
        Asset,
        on_delete=models.PROTECT,
        related_name='positions'
    )
    quantity = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Current holdings quantity"
    )
    average_cost = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Weighted average purchase price per unit (in asset's currency)"
    )
    realized_pnl = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal('0'),
        help_text="Cumulative profit/loss from closed (sold) portions"
    )
    opened_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ['-updated_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'asset'],
                name='unique_user_asset_position'
            )
        ]
        indexes = [
            models.Index(fields=['user', 'asset']),
        ]
        verbose_name = 'Position'
        verbose_name_plural = 'Positions'

    def __str__(self):
        return f"{self.user.email}: {self.quantity} {self.asset.symbol} @ {self.average_cost}"

    @property
    def total_cost_basis(self) -> Decimal:
        """Total amount invested in current holdings."""
        return self.quantity * self.average_cost

    def calculate_unrealized_pnl(self) -> Decimal:
        """
        Calculate unrealized P&L at given market price.
        Call from service layer after fetching current_price from PriceHistory.
        
        Args:
            current_price: Current market price per unit
        Returns:
            Decimal: Unrealized profit/loss
        """
        current_price = self.asset.get_latest_price()
        if self.quantity == 0:
            return Decimal('0')
        current_value = self.quantity * current_price
        return current_value - self.total_cost_basis

    @property
    def is_open(self) -> bool:
        """Check if position has active holdings."""
        return self.quantity > 0



class Trade(models.Model):
    """
    Immutable record of an executed trade (complete or partial order fill).
    One trade per order fill event; an order may have multiple trades.
    
    Service Layer Responsibilities (in services.py):
    - Create Trade record when order is matched/executed
    - Calculate total_value = quantity * price
    - Calculate and apply fees (e.g., 0.1% of total_value)
    - For BUY: Create wallet Transaction with source='BUY', amount=-(total_value + fee)
    - For SELL: Create wallet Transaction with source='SELL', amount=+(total_value - fee)
    - Handle FX conversion if asset.currency != wallet.currency
    - Update linked Position (quantity, average_cost, realized_pnl)
    - Update Order (filled_quantity, status)
    - Atomic transaction to ensure all updates succeed or fail together
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.PROTECT,
        related_name='trades',
        help_text="The order this trade fulfills"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='trades'
    )
    asset = models.ForeignKey(
        Asset,
        on_delete=models.PROTECT,
        related_name='trades'
    )
    side = models.CharField(
        max_length=4,
        choices=OrderSide.choices
    )
    quantity = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        validators=[MinValueValidator(Decimal('0.00000001'))],
        help_text="Quantity traded in this execution"
    )
    price = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        validators=[MinValueValidator(Decimal('0.00000001'))],
        help_text="Execution price per unit (in asset's currency)"
    )
    fee = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Trading fee charged"
    )
    fee_currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        related_name='trade_fees',
        help_text="Currency in which fee is denominated"
    )
    wallet_transaction = models.OneToOneField(
        Transaction,
        on_delete=models.PROTECT,
        related_name='trade',
        null=True,
        blank=True,
        help_text="The wallet Transaction recording currency movement for this trade"
    )
    executed_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-executed_at']
        indexes = [
            models.Index(fields=['user', '-executed_at']),
            models.Index(fields=['asset', '-executed_at']),
            models.Index(fields=['order', 'executed_at']),
        ]
        verbose_name = 'Trade'
        verbose_name_plural = 'Trades'

    def __str__(self):
        return f"{self.get_side_display()} {self.quantity} {self.asset.symbol} @ {self.price}"

    @property
    def total_value(self):
        return self.quantity * self.price

    @property
    def net_amount(self):
        """
        Net amount for BUY (total + fee) or SELL (total - fee).
        Should match the absolute value of wallet_transaction.amount.
        """
        if self.side == OrderSide.BUY:
            return self.total_value + self.fee
        else:  # SELL
            return self.total_value - self.fee
        


class PositionSnapshot(models.Model):
    """
    Optional: Historical snapshot of position state for analytics and reporting.
    
    Service Layer Responsibilities (in services.py):
    - Create snapshot after each position-changing event (trade execution)
    - Fetch current market_price from PriceHistory
    - Calculate unrealized_pnl for the snapshot
    - Use for portfolio performance charts, P&L history, etc.
    """
    position = models.ForeignKey(
        Position,
        on_delete=models.CASCADE,
        related_name='snapshots'
    )
    quantity = models.DecimalField(
        max_digits=20,
        decimal_places=8
    )
    average_cost = models.DecimalField(
        max_digits=20,
        decimal_places=8
    )
    realized_pnl = models.DecimalField(
        max_digits=20,
        decimal_places=2
    )
    market_price = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        null=True,
        blank=True,
        help_text="Market price at time of snapshot"
    )
    unrealized_pnl = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Calculated unrealized P&L at snapshot time"
    )
    snapshot_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-snapshot_at']
        indexes = [
            models.Index(fields=['position', '-snapshot_at']),
        ]
        verbose_name = 'Position Snapshot'
        verbose_name_plural = 'Position Snapshots'

    def __str__(self):
        return f"{self.position.asset.symbol}: {self.quantity} @ {self.snapshot_at.strftime('%Y-%m-%d %H:%M')}"

