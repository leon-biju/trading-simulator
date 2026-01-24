from decimal import Decimal
from trading.models import Order, OrderSide, OrderType
from market.models import Asset, Stock
from wallets.models import Wallet


def place_order(
        user_id: int,
        asset: Asset,
        side: OrderSide,
        quantity: Decimal,
        order_type: OrderType,
        limit_price: Decimal | None = None
) -> Order:
    """
    Creates a new order for the given user and asset.
    """

    # 1. Is the asset available for trading?
    if not asset.is_active:
        raise ValueError(f"Asset {asset.symbol} is not active for trading")
    if isinstance(asset, Stock):
        if not asset.exchange.is_currently_open():
            raise ValueError(f"{asset.exchange} not currently open")
    

    # 2. Does the user have sufficient funds (for BUY orders)?
    if order_type == OrderType.LIMIT:
        if limit_price is None:
            raise ValueError("Limit price must be provided for LIMIT orders")
        cost = quantity * limit_price
    else:
        latest_price = asset.get_latest_price()
        if latest_price is None:
            raise ValueError(f"Latest price for {asset.symbol} is not available")
        cost = quantity * latest_price

    user_wallet = Wallet.objects.get(user_id = user_id, currency=asset.currency)
    
    if cost > user_wallet.balance:
        raise ValueError(f"Insufficient funds on {asset.currency} wallet")

    order = Order.objects.create(
        user_id=user_id,
        asset=asset,
        side=side,
        quantity=quantity,
        filled_quantity=Decimal('0'),
        order_type=order_type,
        limit_price=limit_price
    )

    return order

