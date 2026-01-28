# mypy: disable-error-code=no-untyped-def
# mypy: disable-error-code=no-untyped-call

from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
import datetime
from datetime import time, timedelta
import random
from math import exp, sqrt

from market.models import PriceCandle, Exchange, Currency, Asset
from market.services import create_stock_asset, create_currency_asset
from config.constants import SIMULATION_MU, SIMULATION_SIGMA, SIMULATION_INITIAL_PRICE_RANGE


class Command(BaseCommand):
    """
    Seeds the database with market data for development purposes.
    This includes exchanges, currencies, assets (stocks and currency pairs),
    and optionally, historical price data.
    """

    help = "Seed market data for development"

    def handle(self, *args, **kwargs):
        """Main entry point for the management command."""
        self.stdout.write(self.style.SUCCESS("Seeding market data..."))

        self.clear_data()
        currencies = self.create_currencies()
        exchanges = self.create_exchanges()

        # --- Seed Stocks ---
        generate_stocks_history = self._confirm_generation("stocks")
        self.seed_assets(
            asset_type="stock",
            currencies=currencies,
            exchanges=exchanges,
            generate_history=generate_stocks_history,
        )

        # --- Seed Currency Assets (FX Rates) ---
        generate_fx_history = self._confirm_generation("FX rates")
        self.seed_assets(
            asset_type="currency",
            generate_history=generate_fx_history,
        )

        self.stdout.write(self.style.SUCCESS("Market data seeded successfully! ✅ "))

    def clear_data(self):
        """Clears existing market data from the database."""
        self.stdout.write("Clearing existing market data...")
        PriceCandle.objects.all().delete()
        Asset.objects.all().delete()
        Currency.objects.all().delete()
        Exchange.objects.all().delete()
        self.stdout.write("Cleared existing market data. ✅ ")

    def create_currencies(self):
        """Creates and saves currency objects."""
        self.stdout.write("     Creating currencies...")
        currencies = {
            "GBP": Currency.objects.create(
                code="GBP", name="British Pound Sterling", is_base=True
            ),
            "USD": Currency.objects.create(code="USD", name="United States Dollar"),
            "EUR": Currency.objects.create(code="EUR", name="Euro"),
        }
        self.stdout.write(f"Created {len(currencies)} currencies. ✅ ")
        return currencies

    def create_exchanges(self):
        """Creates and saves exchange objects."""
        self.stdout.write("     Creating exchanges...")
        exchanges_data = [
            {
                "code": "LSE",
                "name": "London Stock Exchange",
                "timezone": "Europe/London",
                "open_time": time(8, 0),
                "close_time": time(16, 30),
            },
            {
                "code": "NYSE",
                "name": "New York Stock Exchange",
                "timezone": "America/New_York",
                "open_time": time(9, 30),
                "close_time": time(16, 0),
            },
            {
                "code": "NASDAQ",
                "name": "NASDAQ",
                "timezone": "America/New_York",
                "open_time": time(9, 30),
                "close_time": time(16, 0),
            },
        ]
        exchanges = {
            data["code"]: Exchange.objects.create(**data) for data in exchanges_data
        }
        self.stdout.write(f"Created {len(exchanges)} exchanges. ✅ ")
        return exchanges

    def seed_assets(self, asset_type, currencies=None, exchanges=None, generate_history=False):
        """
        Seeds assets of a given type (stock or currency) and their price history.
        """
        self.stdout.write(f"     Seeding {asset_type} assets...")

        if asset_type == "stock":
            asset_data = self._get_stocks_data(currencies, exchanges)
            creator_func = create_stock_asset
        elif asset_type == "currency":
            asset_data = self._get_currency_assets_data()
            creator_func = create_currency_asset # type: ignore[assignment]
        else:
            self.stdout.write(self.style.ERROR(f"Unknown asset type: {asset_type}"))
            return

        for data in asset_data:
            price = data.pop("price")
            asset = creator_func(**data)
            self.stdout.write(f"    Created {asset_type} asset: {asset.symbol}")

            if generate_history:
                self._create_price_history(asset, Decimal(price))
            else:
                PriceCandle.objects.create(
                    asset=asset,
                    interval_minutes=1440,
                    start_at=timezone.now(),
                    open_price=Decimal(price).quantize(Decimal("0.0001")),
                    high_price=Decimal(price).quantize(Decimal("0.0001")),
                    low_price=Decimal(price).quantize(Decimal("0.0001")),
                    close_price=Decimal(price).quantize(Decimal("0.0001")),
                    volume=0,
                    source="SEEDING",
                )
                self.stdout.write(
                    f"      Created initial price entry for {asset.symbol}"
                )

        self.stdout.write(
            f"Created {len(asset_data)} {asset_type} assets. ✅ "
        )

    def _get_stocks_data(self, currencies, exchanges):
        """Returns a list of dictionaries for stock assets."""
        return [
            {
                "symbol": "VOD.L",
                "name": "Vodafone Group plc",
                "currency": currencies["GBP"],
                "exchange": exchanges["LSE"],
                "price": "86.48",
            },
            {
                "symbol": "BP.L",
                "name": "BP plc",
                "currency": currencies["GBP"],
                "exchange": exchanges["LSE"],
                "price": "485.0",
            },
            {
                "symbol": "HSBA.L",
                "name": "HSBC Holdings plc",
                "currency": currencies["GBP"],
                "exchange": exchanges["LSE"],
                "price": "642.0",
            },
            {
                "symbol": "AAPL",
                "name": "Apple Inc",
                "currency": currencies["USD"],
                "exchange": exchanges["NASDAQ"],
                "price": "185.50",
            },
            {
                "symbol": "MSFT",
                "name": "Microsoft Corporation",
                "currency": currencies["USD"],
                "exchange": exchanges["NASDAQ"],
                "price": "398.75",
            },
            {
                "symbol": "GOOGL",
                "name": "Alphabet Inc",
                "currency": currencies["USD"],
                "exchange": exchanges["NASDAQ"],
                "price": "142.30",
            },
            {
                "symbol": "SPY",
                "name": "SPDR S&P 500 ETF",
                "currency": currencies["USD"],
                "exchange": exchanges["NYSE"],
                "price": "478.25",
            },
            {
                "symbol": "QQQ",
                "name": "Invesco QQQ Trust",
                "currency": currencies["USD"],
                "exchange": exchanges["NASDAQ"],
                "price": "412.50",
            },
        ]

    def _get_currency_assets_data(self):
        """Returns a list of dictionaries for currency assets."""
        return [
            {"symbol": "USD", "name": "US Dollar", "price": "1.25"},
            {"symbol": "EUR", "name": "Euro", "price": "0.86"},
            {"symbol": "GBP", "name": "British Pound Sterling", "price": "1.00"},
        ]

    def _confirm_generation(self, data_type):
        """
        Asks the user for confirmation to generate historical data.
        """
        try:
            user_input = input(
                f"     Generate 30 days of historical price data for {data_type}? (y/N): "
            )
            confirmed = user_input.lower() == "y"
            if not confirmed:
                self.stdout.write(
                    self.style.WARNING(
                        f"  Skipping generation of historical price data for {data_type}."
                    )
                )
            return confirmed
        except EOFError:
            # Non-interactive environment
            self.stdout.write(
                self.style.WARNING(
                    f"  Non-interactive mode detected. Skipping historical data for {data_type}."
                )
            )
            return False

    def _create_price_history(self, asset, base_price):
        """
        Creates 30 days of simulated price history for an asset using
        Geometric Brownian Motion, matching the simulation logic in simulation.py.
        """
        TIME_STEP_IN_YEARS = 1 / 252  # Assuming 252 trading days in a year

        price_history_batch = []
        current_price = base_price
        
        for days_ago in range(30, 0, -1):
            day = timezone.now().date() - timedelta(days=days_ago)
            if day.isoweekday() > 5:
                # Skip weekends
                continue

            # Simulate price movement using Geometric Brownian Motion
            if asset.symbol == "GBP":
                # Keep GBP stable against itself (base currency)
                open_price = base_price
                close_price = base_price
                high_price = base_price
                low_price = base_price
                volume = 0 # who the hell trades GBP against GBP
            else:
                drift = (SIMULATION_MU - 0.5 * SIMULATION_SIGMA**2) * TIME_STEP_IN_YEARS
                shock = SIMULATION_SIGMA * sqrt(TIME_STEP_IN_YEARS) * random.gauss(0, 1)
                price_change_factor = exp(drift + shock)
                
                # Opening price is the previous day's close
                open_price = current_price
                
                # Simulate intraday volatility for high/low
                intraday_volatility = SIMULATION_SIGMA * sqrt(TIME_STEP_IN_YEARS / 24)  # Reduced for intraday
                
                # Generate high and low based on open price with intraday movements
                high_factor = exp(abs(random.gauss(0, intraday_volatility)))
                low_factor = exp(-abs(random.gauss(0, intraday_volatility)))
                
                high_price = open_price * Decimal(high_factor)
                low_price = open_price * Decimal(low_factor)
                
                # Close price is the result of the daily GBM step
                close_price = open_price * Decimal(price_change_factor)
                
                # Ensure high is highest and low is lowest
                high_price = max(high_price, close_price, open_price)
                low_price = min(low_price, close_price, open_price)
                
                # Update current price for next iteration
                current_price = close_price
                
                # Simulate volume: higher for stocks, lower for currencies
                if asset.asset_type == "STOCK":
                    # Volume between 1M and 50M shares, with some randomness
                    base_volume = random.randint(1_000_000, 50_000_000)
                    # Add volume spike on volatile days
                    volatility_multiplier = 1 + abs(drift + shock) * 5
                    volume = int(base_volume * volatility_multiplier)
                else:  # CURRENCY
                    # FX markets have much higher volume
                    volume = random.randint(100_000_000, 500_000_000)

            price_history_batch.append(
                PriceCandle(
                    asset=asset,
                    interval_minutes=1440,
                    start_at=timezone.make_aware(
                        datetime.datetime.combine(day, time(0, 0)),
                        datetime.timezone.utc,
                    ),
                    open_price=open_price.quantize(Decimal("0.0001")),
                    high_price=high_price.quantize(Decimal("0.0001")),
                    low_price=low_price.quantize(Decimal("0.0001")),
                    close_price=close_price.quantize(Decimal("0.0001")),
                    volume=volume,
                    source="SIMULATION",
                )
            )

        PriceCandle.objects.bulk_create(price_history_batch)
        self.stdout.write(
            f"      Generated 30 days of price history for {asset.symbol}"
        )