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
        limit_price: Decimal = None
) -> Order | str:
    """
    Creates a new order for the given user and asset.
    """

    # 1. Is the asset available for trading?
    if not asset.is_active:
        return "Asset not active"
    if isinstance(asset, Stock):
        if asset.exchange.is_currently_open():
            return f"{asset.exchange} not currently open"
    

    # 2. Does the user have sufficient funds (for BUY orders)?
    if order_type == OrderType.LIMIT:
        cost = quantity * limit_price
    else:
        cost = quantity * asset.get_latest_price()

    user_wallet = Wallet.objects.get(user_id = user_id, currency=asset.currency)
    
    if cost > user_wallet.balance:
        return f"Insufficient funds on {asset.currency} wallet"

    order = Order.objects.create(
        user_id=user_id,
        asset=asset,
        side=side,
        quantity=quantity,
        filled_quantity=quantity,
        order_type=order_type,
        limit_price=limit_price
    )

    #Order validated now we update

    return order

