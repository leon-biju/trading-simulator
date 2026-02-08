from decimal import Decimal
from typing import Any
from market.models import Asset, Currency, FXRate, PriceCandle, Exchange
import datetime


def setup_currencies() -> dict[str, Currency]:
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


def setup_fx_rates() -> dict[str, Decimal]:
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
    
    base_currency = Currency.objects.get(is_base=True)
    for code, rate in DUMMY_RATES.items():
        currency = Currency.objects.get(code=code)
        FXRate.objects.update_or_create(
            base_currency=base_currency,
            target_currency=currency,
            defaults={"rate": rate},
        )
    
    return DUMMY_RATES

def setup_stock_assets() -> dict[str, Any]:
    """
    Create standard stock assets for testing.
    Returns a dict mapping stock symbols to Asset instances.
    (Since behaviour of trading doesn't depend on asset type, we focus on stocks here.)
    """

    open_exchange, _ = Exchange.objects.get_or_create(
        code="OpenEx",
        defaults={
            "name": "Open Exchange",
            "timezone": "Europe/London",
            "open_time": datetime.time(0, 0),
            "close_time": datetime.time(23, 59),
        },

    )

    closed_exchange, _ = Exchange.objects.get_or_create(
        code="ClosedEx",
        defaults={
            "name": "Closed Exchange",
            "timezone": "Europe/London",
            "open_time": datetime.time(23, 58),
            "close_time": datetime.time(23, 59),
        },
    )

    stocks_data = [
        {"symbol": "AAPL", "name": "Apple Inc.", "exchange": open_exchange, "is_active": True},
        {"symbol": "GOOGL", "name": "Alphabet Inc.", "exchange": open_exchange, "is_active": False},
        {"symbol": "MSFT", "name": "Microsoft Corporation", "exchange": closed_exchange, "is_active": True},
    ]

    stocks = {}
    stock_prices = {
        "AAPL": Decimal("150.00"),
        "GOOGL": Decimal("140.00"),
        "MSFT": Decimal("400.00"),
    }
    
    for stock_data in stocks_data:
        stock, created = Asset.objects.get_or_create(
            ticker=stock_data["symbol"],
            exchange=stock_data["exchange"],
            defaults={
                "name": stock_data["name"],
                "asset_type": "STOCK",
                "is_active": stock_data["is_active"],
                "currency": Currency.objects.get(code="USD"),  # Assuming USD
            },
        )

        stocks[stock.ticker] = stock
        
        # Always ensure price history exists for each stock
        # Delete old price history and create fresh to avoid stale data issues
        PriceCandle.objects.filter(asset=stock).delete()
        price = stock_prices.get(stock.ticker, Decimal("100.00"))
        PriceCandle.objects.create(
            asset=stock,
            interval_minutes=1440,
            start_at=datetime.datetime.now(datetime.timezone.utc),
            open_price=price,
            high_price=price,
            low_price=price,
            close_price=price,
            volume=0,
            source="SIMULATION",
        )

    
    return stocks

def setup_complete_market_data() -> dict[str, dict[str, Any]]:
    """
    Convenience function to set up all market data in one call:
    - Currencies
    - FX rates
    
    Returns a dict with all created objects.
    """
    currencies = setup_currencies()
    fx_rates = setup_fx_rates()
    
    return {
        'currencies': currencies,
        'fx_rates': fx_rates,
        'stocks': setup_stock_assets(),
    }
