from decimal import Decimal
from market.models import Currency, CurrencyAsset, PriceHistory


def setup_currencies():
    """
    Create standard currencies for testing.
    Returns a dict mapping currency codes to Currency instances.
    """
    currencies_data = [
        {"code": "USD", "name": "US Dollar", "is_base": False},
        {"code": "EUR", "name": "Euro", "is_base": False},
        {"code": "GBP", "name": "British Pound Sterling", "is_base": True},
    ]

    currencies = {}
    for currency_data in currencies_data:
        currency, _ = Currency.objects.get_or_create(
            code=currency_data["code"],
            defaults={
                "name": currency_data["name"],
                "is_base": currency_data["is_base"],
            },
        )
        currencies[currency.code] = currency
    
    return currencies


def setup_currency_assets():
    """
    Create currency assets for all existing currencies.
    Returns a dict mapping currency codes to CurrencyAsset instances.
    """
    base_currency = Currency.objects.filter(is_base=True).first()
    if not base_currency:
        raise ValueError("No base currency found. Run setup_currencies() first.")
    
    currencies = Currency.objects.all()
    currency_assets = {}
    
    for currency in currencies:
        asset, _ = CurrencyAsset.objects.get_or_create(
            symbol=currency.code,
            defaults={
                "asset_type": "CURRENCY",
                "name": currency.name,
                "currency": base_currency,
                "is_active": True,
            },
        )
        currency_assets[currency.code] = asset
    
    return currency_assets


def setup_fx_rates():
    """
    Add dummy FX rates for testing.
    Rates are relative to GBP (base currency).
    Returns a dict mapping currency codes to their exchange rates.
    """
    DUMMY_RATES = {
        "USD": Decimal("1.25"),  # 1 GBP = 1.25 USD
        "EUR": Decimal("1.10"),  # 1 GBP = 1.10 EUR
        "GBP": Decimal("1.0"),   # 1 GBP = 1 GBP
    }
    
    currency_assets = CurrencyAsset.objects.filter(symbol__in=DUMMY_RATES.keys())
    
    price_history_entries = []
    for asset in currency_assets:
        # Check if price already exists to avoid duplicates
        existing = PriceHistory.objects.filter(asset=asset).first()
        if not existing:
            entry = PriceHistory(
                asset=asset,
                price=DUMMY_RATES[asset.symbol],
                source='SIMULATION',
            )
            price_history_entries.append(entry)
    
    if price_history_entries:
        PriceHistory.objects.bulk_create(price_history_entries)
    
    return DUMMY_RATES


def setup_complete_market_data():
    """
    Convenience function to set up all market data in one call:
    - Currencies
    - Currency assets
    - FX rates
    
    Returns a dict with all created objects.
    """
    currencies = setup_currencies()
    currency_assets = setup_currency_assets()
    fx_rates = setup_fx_rates()
    
    return {
        'currencies': currencies,
        'currency_assets': currency_assets,
        'fx_rates': fx_rates,
    }
