from decimal import Decimal
from typing import Optional
import datetime
from django.db import transaction, models
from django.utils import timezone
from django.contrib.auth import get_user_model

from trading.models import PortfolioSnapshot
from market.models import Currency
from wallets.models import Wallet

from market.services.fx import get_fx_conversion

from trading.services.queries import get_user_positions
from trading.services.utils import round_to_two_dp


def create_portfolio_snapshot(user_id: int) -> PortfolioSnapshot:
    """
    Create a daily portfolio snapshot for a user.
    
    Calculates the total portfolio value, cost basis, and cash balance,
    converting everything to the base currency.
    
    Args:
        user_id: The user to create a snapshot for
        
    Returns:
        PortfolioSnapshot: The created or updated snapshot
        
    Raises:
        LookupError: If base currency is not configured
    """
    
    base_currency = Currency.objects.filter(is_base=True).first()
    if not base_currency:
        raise LookupError("Base currency not configured")
    
    today = timezone.now().date()
    
    # Calculate total portfolio value and cost from positions
    positions = get_user_positions(user_id)
    total_value = Decimal('0')
    total_cost = Decimal('0')
    
    for position in positions:
        current_price = position.asset.get_latest_price()
        if current_price is None:
            current_price = position.average_cost  # Fallback to average cost
        
        position_value = position.quantity * current_price
        position_cost = position.total_cost_basis
        
        # Convert to base currency
        _, position_value_base = get_fx_conversion(
            from_currency_code=position.asset.currency.code,
            to_currency_code=base_currency.code,
            from_amount=position_value,
            to_amount=None
        )

        _, position_cost_base = get_fx_conversion(
            from_currency_code=position.asset.currency.code,
            to_currency_code=base_currency.code,
            from_amount=position_cost,
            to_amount=None
        )
        
        total_value += position_value_base
        total_cost += position_cost_base
    
    # Calculate total cash balance across all wallets
    wallets = Wallet.objects.filter(user_id=user_id).select_related('currency')
    total_cash = Decimal('0')
    
    for wallet in wallets:
        _, wallet_balance_base = get_fx_conversion(
            from_currency_code=wallet.currency.code,
            to_currency_code=base_currency.code,
            from_amount=wallet.balance,
            to_amount=None
        )

        total_cash += wallet_balance_base
    
    # Create or update the snapshot for today
    snapshot, _ = PortfolioSnapshot.objects.update_or_create(
        user_id=user_id,
        date=today,
        defaults={
            'total_value': total_value,
            'total_cost': total_cost,
            'cash_balance': total_cash,
        }
    )
    
    return snapshot


def get_portfolio_history(
    user_id: int,
    days: int | None = None,
) -> list[PortfolioSnapshot]:
    """
    Get portfolio history for a user.
    
    Args:
        user_id: The user to get history for
        days: Number of days to look back (None for all history)
        
    Returns:
        List of PortfolioSnapshot ordered by date ascending (oldest first)
    """    
    queryset = PortfolioSnapshot.objects.filter(user_id=user_id)
    
    if days is not None:
        start_date = timezone.now().date() - datetime.timedelta(days=days)
        queryset = queryset.filter(date__gte=start_date)
    
    return list(queryset.order_by('date'))


def snapshot_all_user_portfolios() -> dict[str, int]:
    """
    Create portfolio snapshots for all users
    
    Returns:
        dict with counts of successful and failed snapshots
    """
    User = get_user_model()
    
    results = {
        'success': 0,
        'failed': 0,
    }
    
    users = User.objects.all()
    
    for user in users:
        try:
            create_portfolio_snapshot(user.id)
            results['success'] += 1
        except Exception:
            results['failed'] += 1
    
    return results
