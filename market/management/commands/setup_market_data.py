import json
from decimal import Decimal
from typing import Iterable

from django.conf import settings

from django.core.management import call_command
from django.core.management.base import BaseCommand

from market.api_access import get_currency_layer_api_data
from market.models import Asset, Currency, Exchange, FXRate, PriceCandle
from market.services.fx import update_currency_prices


class Command(BaseCommand):
    help = "Interactive database setup wizard for a fresh install."

    def add_arguments(self, parser):  # type: ignore[no-untyped-def]
        parser.add_argument(
            "--force",
            action="store_true",
            help="Run even if market data already exists.",
        )

    def handle(self, *args, **options):  # type: ignore[no-untyped-def]
        force = options.get("force", False)
        if self._has_existing_market_data() and not force:
            self.stdout.write(
                self.style.WARNING(
                    "Market data already exists. Run with --force to continue."
                )
            )
            return

        if self._has_existing_market_data() and force:
            self.stdout.write(
                self.style.WARNING(
                    "Warning: This will wipe existing market data! Confirm that you want to continue (y/N): "
                )
            )
            confirm = input().strip().lower()
            if confirm != "y":
                self.stdout.write("Cancelling database initialization.")
                return

        self.stdout.write(self.style.MIGRATE_HEADING("Database setup wizard"))

        currencies = self._prompt_currencies()
        base_code = self._prompt_base_currency(currencies)
        base_currency = self._create_currencies(currencies, base_code)

        self.stdout.write(
            "Loading exchanges and assets from market/data/exchanges.json and market/data/assets.json"
        )
        self._load_exchanges()
        self._load_assets()

        self._seed_fx_rates(base_currency)


        mode = self._prompt_mode()
        if mode == "simulation":
            self._prompt_backfill()
        else:
            self.stdout.write("Live data mode not implemented yet.")

        self.stdout.write(self.style.SUCCESS("Database initialization complete."))
        self.stdout.write("Remember to create a superuser with 'python manage.py createsuperuser'.")

    def _has_existing_market_data(self) -> bool:
        return (
            Currency.objects.exists()
            or FXRate.objects.exists()
            or Exchange.objects.exists()
            or Asset.objects.exists()
            or PriceCandle.objects.exists()
        )

    def _prompt_currencies(self) -> list[tuple[str, str]]:
        default = [
            ("GBP", "British Pound Sterling"),
            ("USD", "US Dollar"),
            ("EUR", "Euro"),
            ("JPY", "Japanese Yen"),
            ("CHF", "Swiss Franc"),
            ("AUD", "Australian Dollar"),
            ("CAD", "Canadian Dollar"),
            ("CNY", "Chinese Yuan"),
            ("HKD", "Hong Kong Dollar"),
        ]

        default_str = ", ".join(f"{code}:{name}" for code, name in default)
        self.stdout.write(
            "Enter currencies as CODE:Name, comma-separated. Example:"
        )
        self.stdout.write(f"  {default_str}")
        self.stdout.write("Leave blank to use the default set above.")


        while True:
            raw = input("Currencies: ").strip()
            if not raw:
                return default

            parsed = self._parse_currency_input(raw)
            if parsed:
                return parsed

            self.stdout.write(
                self.style.ERROR(
                    "Invalid format. Use CODE:Name pairs separated by commas."
                )
            )

    def _parse_currency_input(self, raw: str) -> list[tuple[str, str]]:
        pairs: list[tuple[str, str]] = []
        for chunk in raw.split(","):
            part = chunk.strip()
            if not part:
                continue

            if ":" not in part:
                return []

            code, name = [item.strip() for item in part.split(":", 1)]
            code = code.upper()
            if len(code) != 3 or not code.isalpha() or not name:
                return []

            pairs.append((code, name))

        unique_codes = {code for code, _ in pairs}
        if len(unique_codes) != len(pairs):
            return []

        return pairs

    def _prompt_base_currency(self, currencies: Iterable[tuple[str, str]]) -> str:
        currency_codes = [code for code, _ in currencies]
        default = currency_codes[0]
        self.stdout.write(
            f"Select base currency [{default}]. Options: {', '.join(currency_codes)}"
        )

        while True:
            raw = input("Base currency: ").strip().upper()
            if not raw:
                return default

            if raw in currency_codes:
                return raw

            self.stdout.write(self.style.ERROR("Base currency must be in the list."))

    def _create_currencies(
        self,
        currencies: Iterable[tuple[str, str]],
        base_code: str,
    ) -> Currency:
        base_currency: Currency | None = None
        for code, name in currencies:
            currency, _ = Currency.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "is_base": code == base_code,
                },
            )
            
            if code == base_code:
                base_currency = currency

        if base_currency is None:
            raise RuntimeError("Base currency was not created.")

        self.stdout.write(self.style.SUCCESS("Currencies saved."))
        return base_currency

    def _seed_fx_rates(self, base_currency: Currency) -> None:
        api_data = get_currency_layer_api_data()
        if api_data and not api_data.get("skipped"):
            updated = update_currency_prices(api_data)
            self.stdout.write(
                self.style.SUCCESS(f"FX rates updated from API: {updated}")
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "FX rate API unavailable. Seeding 1.0 rates for all currencies."
                )
            )
            currencies = Currency.objects.all()
            for currency in currencies:
                FXRate.objects.update_or_create(
                    base_currency=base_currency,
                    target_currency=currency,
                    defaults={"rate": Decimal("1.0")},
                )

        FXRate.objects.update_or_create(
            base_currency=base_currency,
            target_currency=base_currency,
            defaults={"rate": Decimal("1.0")},
        )

    def _load_exchanges(self) -> None:
        exchanges_path = settings.BASE_DIR / "market" / "data" / "exchanges.json"
        if not exchanges_path.exists():
            self.stdout.write(self.style.WARNING("No exchanges.json found. Skipping."))
            return

        with exchanges_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        created = 0
        for item in data:
            _, was_created = Exchange.objects.update_or_create(
                code=item["code"],
                defaults={
                    "name": item["name"],
                    "timezone": item["timezone"],
                    "open_time": item["open_time"],
                    "close_time": item["close_time"],
                },
            )
            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(f"Exchanges loaded. Created: {created}"))

    def _load_assets(self) -> None:
        assets_path = settings.BASE_DIR / "market" / "data" / "assets.json"
        if not assets_path.exists():
            self.stdout.write(self.style.WARNING("No assets.json found. Skipping."))
            return

        with assets_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        skipped_currencies: set[str] = set()
        created = 0
        updated = 0

        for item in data:
            currency_code = item["currency_code"].upper()
            if currency_code in skipped_currencies:
                continue

            currency = Currency.objects.filter(code=currency_code).first()
            if currency is None:
                if not self._prompt_add_currency(currency_code):
                    skipped_currencies.add(currency_code)
                    continue
                currency = self._create_currency(currency_code)

            exchange = Exchange.objects.filter(code=item["exchange_code"]).first()
            if exchange is None:
                self.stdout.write(
                    self.style.WARNING(
                        f"Exchange {item['exchange_code']} not found. Skipping {item['ticker']}."
                    )
                )
                continue

            asset, was_created = Asset.objects.update_or_create(
                ticker=item["ticker"],
                exchange=exchange,
                defaults={
                    "name": item["name"],
                    "asset_type": item["asset_type"],
                    "currency": currency,
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Assets loaded. Created: {created}, Updated: {updated}, Skipped currencies: {len(skipped_currencies)}"
            )
        )

    def _prompt_add_currency(self, currency_code: str) -> bool:
        raw = input(
            f"Currency {currency_code} not found. Add it? (y/N): "
        ).strip().lower()
        return raw in {"y", "yes"}

    def _create_currency(self, currency_code: str) -> Currency:
        raw_name = input(
            f"Currency name for {currency_code} [{currency_code}]: "
        ).strip()
        name = raw_name or currency_code
        currency, _ = Currency.objects.get_or_create(
            code=currency_code,
            defaults={"name": name, "is_base": False},
        )
        return currency

    def _prompt_mode(self) -> str:
        self.stdout.write("Select mode: simulation or live.")
        self.stdout.write(
            self.style.WARNING("Note: Live data mode is not yet implemented.")
        )
        while True:
            raw = input("Mode [simulation]: ").strip().lower()
            if not raw or raw == "simulation":
                return "simulation"
            if raw == "live":
                self.stdout.write(
                    self.style.ERROR(
                        "Live mode is not available yet. Please choose simulation."
                    )
                )
                continue
            self.stdout.write(self.style.ERROR("Enter 'simulation' or 'live'."))

    def _prompt_backfill(self) -> None:
        raw = input("Backfill simulated price history now? (y/N): ").strip().lower()
        if raw not in {"y", "yes"}:
            return

        days = self._prompt_int("Days to backfill", default=365)
        intraday_days = self._prompt_int("Intraday days", default=7)
        interval_minutes = self._prompt_int("Intraday interval minutes", default=5)
        reset = self._prompt_bool("Reset existing price history", default=False)

        call_command(
            "backfill_price_history",
            days=days,
            intraday_days=intraday_days,
            interval_minutes=interval_minutes,
            reset=reset,
        )

    def _prompt_int(self, label: str, *, default: int) -> int:
        while True:
            raw = input(f"{label} [{default}]: ").strip()
            if not raw:
                return default
            try:
                value = int(raw)
            except ValueError:
                self.stdout.write(self.style.ERROR("Enter a valid integer."))
                continue
            if value <= 0:
                self.stdout.write(self.style.ERROR("Value must be positive."))
                continue
            return value

    def _prompt_bool(self, label: str, *, default: bool) -> bool:
        default_label = "y" if default else "n"
        raw = input(f"{label} (y/N) [{default_label}]: ").strip().lower()
        if not raw:
            return default
        return raw in {"y", "yes"}
