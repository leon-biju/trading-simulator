from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from datetime import time, timedelta
import random

from apps.market.models import Exchange, Currency, PriceHistory, Asset
from apps.market.services import create_stock_asset, create_currency_asset


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

        self.stdout.write(self.style.SUCCESS("✅ Market data seeded successfully!"))

    def clear_data(self):
        """Clears existing market data from the database."""
        self.stdout.write("  🗑️  Clearing existing market data...")
        PriceHistory.objects.all().delete()
        Asset.objects.all().delete()
        Currency.objects.all().delete()
        Exchange.objects.all().delete()
        self.stdout.write("  ✅  Cleared existing market data.")

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
        self.stdout.write(f"  ✅  Created {len(currencies)} currencies.")
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
        self.stdout.write(f"  ✅  Created {len(exchanges)} exchanges.")
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
            creator_func = create_currency_asset
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
                PriceHistory.objects.create(
                    asset=asset,
                    timestamp=timezone.now(),
                    price=Decimal(price).quantize(Decimal("0.0001")),
                    source="SEEDING",
                )
                self.stdout.write(
                    f"      Created initial price entry for {asset.symbol}"
                )

        self.stdout.write(
            f"  ✅  Created {len(asset_data)} {asset_type} assets."
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
        Creates 30 days of simulated price history for an asset.
        """
        price_history_batch = []
        for days_ago in range(30, 0, -1):
            timestamp = timezone.now() - timedelta(days=days_ago)

            # Simulate price movement, keeping GBP stable against itself
            if asset.symbol == "GBP":
                price = base_price
            else:
                variance = Decimal(random.uniform(-0.05, 0.05))
                price = base_price * (1 + variance)

            price_history_batch.append(
                PriceHistory(
                    asset=asset,
                    timestamp=timestamp,
                    price=price.quantize(Decimal("0.0001")),
                    source="SIMULATION",
                )
            )

        PriceHistory.objects.bulk_create(price_history_batch)
        self.stdout.write(
            f"      Generated 30 days of price history for {asset.symbol}"
        )