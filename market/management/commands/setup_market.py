"""
Single entry point for setting up market data on a fresh install.

Replaces setup_market_data + seed_assets + backfill_asset_history.

Flow:
  1. Select indices (drives everything else)
  2. Create exchanges and currencies derived from selection
  3. Seed FX rates
  4. Scrape Wikipedia for constituents
  5. Download real OHLC from Yahoo Finance
  6. GBM simulation continues from the seeded prices
"""

import concurrent.futures
import datetime
from decimal import Decimal

import pandas as pd
import yfinance as yf
from django.core.management.base import BaseCommand, CommandError

from market.api_access import get_currency_layer_api_data
from market.models import Asset, Currency, Exchange, FXRate, PriceCandle
from market.services.candles import get_asset_timezone
from market.services.fx import update_currency_prices

_BATCH = 100  # tickers per yfinance download call

# All metadata in one place. Exchanges and currencies are derived from
# whichever indices the user picks — nothing lives in JSON files.
INDICES: dict[str, dict] = {
    "sp500": {
        "name": "S&P 500",
        "exchanges": [
            {
                "code": "NYSE",
                "name": "New York Stock Exchange",
                "timezone": "America/New_York",
                "open_time": "09:30:00",
                "close_time": "16:00:00",
            },
            {
                "code": "NASDAQ",
                "name": "NASDAQ",
                "timezone": "America/New_York",
                "open_time": "09:30:00",
                "close_time": "16:00:00",
            },
        ],
        "default_exchange": None,  # resolved per-ticker via yfinance
        "currency": ("USD", "US Dollar"),
        "yf_suffix": "",
        "approx": 503,
    },
    "ftse100": {
        "name": "FTSE 100",
        "exchanges": [
            {
                "code": "LSE",
                "name": "London Stock Exchange",
                "timezone": "Europe/London",
                "open_time": "08:00:00",
                "close_time": "16:30:00",
            },
        ],
        "default_exchange": "LSE",
        "currency": ("GBP", "British Pound Sterling"),
        "yf_suffix": ".L",
        "approx": 100,
    },
    "nikkei225": {
        "name": "Nikkei 225",
        "exchanges": [
            {
                "code": "JPX",
                "name": "Japan Exchange Group",
                "timezone": "Asia/Tokyo",
                "open_time": "09:00:00",
                "close_time": "15:00:00",
            },
        ],
        "default_exchange": "JPX",
        "currency": ("JPY", "Japanese Yen"),
        "yf_suffix": ".T",
        "approx": 225,
    },
    "hangseng": {
        "name": "Hang Seng Index",
        "exchanges": [
            {
                "code": "HKEX",
                "name": "Hong Kong Stock Exchange",
                "timezone": "Asia/Hong_Kong",
                "open_time": "09:30:00",
                "close_time": "16:00:00",
            },
        ],
        "default_exchange": "HKEX",
        "currency": ("HKD", "Hong Kong Dollar"),
        "yf_suffix": ".HK",
        "approx": 80,
    },
    "cac40": {
        "name": "CAC 40",
        "exchanges": [
            {
                "code": "EPA",
                "name": "Euronext Paris",
                "timezone": "Europe/Paris",
                "open_time": "09:00:00",
                "close_time": "17:30:00",
            },
        ],
        "default_exchange": "EPA",
        "currency": ("EUR", "Euro"),
        "yf_suffix": ".PA",
        "approx": 40,
    },
    "smi": {
        "name": "Swiss Market Index",
        "exchanges": [
            {
                "code": "SIX",
                "name": "SIX Swiss Exchange",
                "timezone": "Europe/Zurich",
                "open_time": "09:00:00",
                "close_time": "17:30:00",
            },
        ],
        "default_exchange": "SIX",
        "currency": ("CHF", "Swiss Franc"),
        "yf_suffix": ".SW",
        "approx": 20,
    },
    "tsx60": {
        "name": "S&P/TSX 60",
        "exchanges": [
            {
                "code": "TSX",
                "name": "Toronto Stock Exchange",
                "timezone": "America/Toronto",
                "open_time": "09:30:00",
                "close_time": "16:00:00",
            },
        ],
        "default_exchange": "TSX",
        "currency": ("CAD", "Canadian Dollar"),
        "yf_suffix": ".TO",
        "approx": 60,
    },
    "asx200": {
        "name": "S&P/ASX 200",
        "exchanges": [
            {
                "code": "ASX",
                "name": "Australian Securities Exchange",
                "timezone": "Australia/Sydney",
                "open_time": "10:00:00",
                "close_time": "16:00:00",
            },
        ],
        "default_exchange": "ASX",
        "currency": ("AUD", "Australian Dollar"),
        "yf_suffix": ".AX",
        "approx": 200,
    },
}

_YF_EXCHANGE_TO_DB: dict[str, str] = {
    "NMS": "NASDAQ",
    "NGM": "NASDAQ",
    "NCM": "NASDAQ",
    "NYQ": "NYSE",
    "ASE": "NYSE",
    "PCX": "NYSE",
    "BTS": "NYSE",
}


class Command(BaseCommand):
    help = "Set up all market data for a fresh install: exchanges, currencies, FX rates, assets, and price history."

    def add_arguments(self, parser):  # type: ignore[no-untyped-def]
        parser.add_argument(
            "--index",
            nargs="+",
            choices=list(INDICES.keys()),
            help="Skip the interactive prompt and seed specific indices. E.g. --index sp500 ftse100",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=365,
            help="Days of daily candle history to seed (default: 365).",
        )
        parser.add_argument(
            "--intraday-days",
            type=int,
            default=7,
            help="Days of intraday (5-min/hourly) history (default: 7).",
        )
        parser.add_argument(
            "--no-prices",
            action="store_true",
            help="Create assets only, skip price seeding.",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing candles for affected assets before seeding.",
        )
        parser.add_argument(
            "--workers",
            type=int,
            default=20,
            help="Threads for parallel NYSE/NASDAQ resolution (default: 20).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Run even if market data already exists.",
        )

    def handle(self, *args, **options):  # type: ignore[no-untyped-def]
        if self._has_existing_data() and not options["force"]:
            self.stdout.write(
                self.style.WARNING("Market data already exists. Use --force to continue.")
            )
            return

        if self._has_existing_data() and options["force"]:
            confirm = input("This will add to existing data. Continue? (y/N): ").strip().lower()
            if confirm != "y":
                return

        self.stdout.write(self.style.MIGRATE_HEADING("Market setup"))

        # ── 1. Index selection ────────────────────────────────────────────────
        selected_keys: list[str] = options["index"] or self._prompt_index_selection()

        # ── 2. Exchanges ──────────────────────────────────────────────────────
        exchange_defs = self._collect_exchanges(selected_keys)
        self._create_exchanges(exchange_defs)

        # ── 3. Currencies + base ──────────────────────────────────────────────
        currency_defs = self._collect_currencies(selected_keys)
        base_currency = self._setup_currencies(currency_defs)

        # ── 4. FX rates ───────────────────────────────────────────────────────
        self._seed_fx_rates(base_currency)

        # ── 5. Assets ─────────────────────────────────────────────────────────
        # ticker_data: db_ticker -> {name, exchange_code, currency_code, yf_ticker}
        ticker_data: dict[str, dict] = {}
        for key in selected_keys:
            conf = INDICES[key]
            rows = self._scrape_index(key)
            if not rows:
                self.stdout.write(self.style.WARNING(f"No tickers scraped for {conf['name']}. Skipping."))
                continue
            for db_ticker, name in rows:
                if len(db_ticker) > 10:
                    continue
                ticker_data.setdefault(db_ticker, {
                    "name": name,
                    "exchange_code": conf["default_exchange"],
                    "currency_code": conf["currency"][0],
                    "yf_ticker": db_ticker.replace(".", "-") + conf["yf_suffix"],
                })
            self.stdout.write(self.style.SUCCESS(f"  {conf['name']}: {len(rows)} tickers scraped."))

        if not ticker_data:
            raise CommandError("No tickers collected — aborting.")

        us_unresolved = [t for t, d in ticker_data.items() if d["exchange_code"] is None]
        if us_unresolved:
            self.stdout.write(
                f"Resolving NYSE/NASDAQ for {len(us_unresolved)} US tickers..."
            )
            self._resolve_us_exchanges(us_unresolved, ticker_data, options["workers"])

        assets = self._create_assets(ticker_data)
        self.stdout.write(self.style.SUCCESS(f"Assets created/updated: {len(assets)}"))

        # ── 6. Prices ─────────────────────────────────────────────────────────
        if options["no_prices"]:
            self.stdout.write("Skipping price seeding (--no-prices).")
        else:
            if options["reset"]:
                deleted, _ = PriceCandle.objects.filter(asset__in=list(assets.values())).delete()
                self.stdout.write(self.style.WARNING(f"Cleared {deleted} existing candles."))
            self._seed_prices(assets, ticker_data, options["days"], options["intraday_days"])

        self.stdout.write(self.style.SUCCESS("Setup complete."))
        self.stdout.write("Run 'python manage.py createsuperuser' to create an admin account.")

    # ── Existence check ───────────────────────────────────────────────────────

    def _has_existing_data(self) -> bool:
        return (
            Currency.objects.exists()
            or FXRate.objects.exists()
            or Exchange.objects.exists()
            or Asset.objects.exists()
            or PriceCandle.objects.exists()
        )

    # ── Index selection ───────────────────────────────────────────────────────

    def _prompt_index_selection(self) -> list[str]:
        self.stdout.write("\nAvailable indices:")
        keys = list(INDICES.keys())
        for i, key in enumerate(keys, 1):
            c = INDICES[key]
            currency_code = c["currency"][0]
            self.stdout.write(f"  {i}. {c['name']}  (~{c['approx']} stocks, {currency_code})")
        self.stdout.write(f"  {len(keys) + 1}. All of the above")
        self.stdout.write("Enter numbers separated by commas, or press Enter for all:")

        while True:
            raw = input().strip()
            if not raw:
                return keys
            try:
                nums = [int(x.strip()) for x in raw.split(",")]
                if len(keys) + 1 in nums:
                    return keys
                selected = [keys[n - 1] for n in nums if 1 <= n <= len(keys)]
                if selected:
                    return list(dict.fromkeys(selected))
            except (ValueError, IndexError):
                pass
            self.stdout.write(self.style.ERROR("Invalid input. Enter numbers like 1,3 or press Enter for all:"))

    # ── Exchange setup ────────────────────────────────────────────────────────

    def _collect_exchanges(self, selected_keys: list[str]) -> list[dict]:
        seen: set[str] = set()
        result: list[dict] = []
        for key in selected_keys:
            for ex in INDICES[key]["exchanges"]:
                if ex["code"] not in seen:
                    seen.add(ex["code"])
                    result.append(ex)
        return result

    def _create_exchanges(self, exchange_defs: list[dict]) -> None:
        created = 0
        for ex in exchange_defs:
            _, was_created = Exchange.objects.update_or_create(
                code=ex["code"],
                defaults={
                    "name": ex["name"],
                    "timezone": ex["timezone"],
                    "open_time": ex["open_time"],
                    "close_time": ex["close_time"],
                },
            )
            if was_created:
                created += 1
        self.stdout.write(self.style.SUCCESS(f"Exchanges ready. Created: {created}"))

    # ── Currency setup ────────────────────────────────────────────────────────

    def _collect_currencies(self, selected_keys: list[str]) -> list[tuple[str, str]]:
        seen: set[str] = set()
        result: list[tuple[str, str]] = []
        for key in selected_keys:
            code, name = INDICES[key]["currency"]
            if code not in seen:
                seen.add(code)
                result.append((code, name))
        return result

    def _setup_currencies(self, currency_defs: list[tuple[str, str]]) -> Currency:
        codes = [c for c, _ in currency_defs]
        self.stdout.write(f"Currencies from selected indices: {', '.join(codes)}")
        default = "USD" if "USD" in codes else codes[0]

        while True:
            raw = input(f"Base currency [{default}]: ").strip().upper()
            base_code = raw or default
            if base_code in codes:
                break
            self.stdout.write(self.style.ERROR(f"Choose from: {', '.join(codes)}"))

        base: Currency | None = None
        for code, name in currency_defs:
            obj, _ = Currency.objects.update_or_create(
                code=code,
                defaults={"name": name, "is_base": code == base_code},
            )
            if code == base_code:
                base = obj

        if base is None:
            raise RuntimeError("Base currency was not created.")

        self.stdout.write(self.style.SUCCESS(f"Currencies ready. Base: {base_code}"))
        return base

    # ── FX rates ──────────────────────────────────────────────────────────────

    def _seed_fx_rates(self, base_currency: Currency) -> None:
        api_data = get_currency_layer_api_data()
        if api_data and not api_data.get("skipped"):
            updated = update_currency_prices(api_data)
            self.stdout.write(self.style.SUCCESS(f"FX rates updated from API: {updated}"))
        else:
            self.stdout.write(self.style.WARNING("FX API unavailable. Seeding 1.0 rates."))
            for currency in Currency.objects.all():
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

    # ── Wikipedia scrapers ────────────────────────────────────────────────────

    def _scrape_index(self, key: str) -> list[tuple[str, str]]:
        try:
            return {
                "sp500": self._scrape_sp500,
                "ftse100": self._scrape_ftse100,
                "nikkei225": self._scrape_nikkei225,
                "hangseng": self._scrape_hangseng,
                "cac40": self._scrape_cac40,
                "smi": self._scrape_smi,
                "tsx60": self._scrape_tsx60,
                "asx200": self._scrape_asx200,
            }[key]()
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f"Scrape failed for {key}: {exc}"))
            return []

    def _scrape_sp500(self) -> list[tuple[str, str]]:
        tables = pd.read_html(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
            attrs={"id": "constituents"},
        )
        df = tables[0]
        return [(str(r["Symbol"]).strip(), str(r["Security"]).strip()) for _, r in df.iterrows()]

    def _scrape_ftse100(self) -> list[tuple[str, str]]:
        return self._scrape_generic(
            "https://en.wikipedia.org/wiki/FTSE_100_Index",
            ticker_cols=("epic", "ticker", "symbol"),
            name_cols=("company", "name", "security"),
            min_rows=80,
        )

    def _scrape_nikkei225(self) -> list[tuple[str, str]]:
        return self._scrape_generic(
            "https://en.wikipedia.org/wiki/Nikkei_225",
            ticker_cols=("code", "ticker", "symbol"),
            name_cols=("company", "name", "security"),
            min_rows=100,
        )

    def _scrape_hangseng(self) -> list[tuple[str, str]]:
        rows = self._scrape_generic(
            "https://en.wikipedia.org/wiki/Hang_Seng_Index",
            ticker_cols=("code", "ticker", "symbol", "constituent stocks"),
            name_cols=("company", "name", "constituent", "english name"),
            min_rows=30,
        )
        result = []
        for ticker, name in rows:
            try:
                result.append((str(int(float(ticker))).zfill(4), name))
            except ValueError:
                result.append((ticker, name))
        return result

    def _scrape_cac40(self) -> list[tuple[str, str]]:
        return self._scrape_generic(
            "https://en.wikipedia.org/wiki/CAC_40",
            ticker_cols=("ticker", "symbol"),
            name_cols=("company", "name"),
            min_rows=35,
        )

    def _scrape_smi(self) -> list[tuple[str, str]]:
        return self._scrape_generic(
            "https://en.wikipedia.org/wiki/Swiss_Market_Index",
            ticker_cols=("ticker", "symbol"),
            name_cols=("company", "name", "constituent"),
            min_rows=15,
        )

    def _scrape_tsx60(self) -> list[tuple[str, str]]:
        return self._scrape_generic(
            "https://en.wikipedia.org/wiki/S%26P/TSX_60",
            ticker_cols=("ticker", "symbol"),
            name_cols=("company", "name", "constituent"),
            min_rows=50,
        )

    def _scrape_asx200(self) -> list[tuple[str, str]]:
        return self._scrape_generic(
            "https://en.wikipedia.org/wiki/S%26P/ASX_200",
            ticker_cols=("code", "ticker", "asx code", "symbol"),
            name_cols=("company", "name", "constituent"),
            min_rows=100,
        )

    def _scrape_generic(
        self,
        url: str,
        ticker_cols: tuple[str, ...],
        name_cols: tuple[str, ...],
        min_rows: int = 10,
    ) -> list[tuple[str, str]]:
        for df in pd.read_html(url):
            if len(df) < min_rows:
                continue
            flat = {str(c).lower().strip(): c for c in df.columns}
            ticker_col = next((flat[k] for k in ticker_cols if k in flat), None)
            name_col = next((flat[k] for k in name_cols if k in flat), None)
            if ticker_col and name_col:
                return [
                    (str(r[ticker_col]).strip(), str(r[name_col]).strip())
                    for _, r in df.iterrows()
                    if str(r[ticker_col]).strip() not in ("nan", "", "None")
                ]
        raise ValueError(f"No matching constituents table found at {url}")

    # ── Exchange resolution (S&P 500) ─────────────────────────────────────────

    def _resolve_us_exchanges(
        self, tickers: list[str], ticker_data: dict, workers: int
    ) -> None:
        def lookup(ticker: str) -> tuple[str, str]:
            try:
                code = yf.Ticker(ticker.replace(".", "-")).fast_info.exchange
                return ticker, _YF_EXCHANGE_TO_DB.get(code or "", "NYSE")
            except Exception:
                return ticker, "NYSE"

        resolved = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(lookup, t): t for t in tickers}
            for future in concurrent.futures.as_completed(futures):
                db_ticker, exchange_code = future.result()
                ticker_data[db_ticker]["exchange_code"] = exchange_code
                resolved += 1
                if resolved % 100 == 0:
                    self.stdout.write(f"  {resolved}/{len(tickers)} resolved...")

    # ── Asset creation ────────────────────────────────────────────────────────

    def _create_assets(self, ticker_data: dict) -> dict[str, Asset]:
        assets: dict[str, Asset] = {}
        skipped = 0
        for db_ticker, data in ticker_data.items():
            exchange = Exchange.objects.filter(code=data.get("exchange_code") or "").first()
            currency = Currency.objects.filter(code=data["currency_code"]).first()
            if not exchange or not currency:
                skipped += 1
                continue
            asset, _ = Asset.objects.update_or_create(
                ticker=db_ticker,
                exchange=exchange,
                defaults={
                    "name": data["name"][:100],
                    "asset_type": "STOCK",
                    "currency": currency,
                    "is_active": True,
                },
            )
            assets[db_ticker] = asset
        if skipped:
            self.stdout.write(self.style.WARNING(f"Skipped {skipped} tickers (exchange or currency not in DB)."))
        return assets

    # ── Price seeding ─────────────────────────────────────────────────────────

    def _seed_prices(
        self,
        assets: dict[str, Asset],
        ticker_data: dict,
        days: int,
        intraday_days: int,
    ) -> None:
        triplets = [
            (db_ticker, ticker_data[db_ticker]["yf_ticker"], asset)
            for db_ticker, asset in assets.items()
        ]
        batches = list(self._chunks(triplets, _BATCH))

        now = datetime.datetime.now(tz=datetime.timezone.utc)
        intervals = [
            (1440, now - datetime.timedelta(days=days), "1d"),
            (60,   now - datetime.timedelta(days=min(intraday_days * 10, 60)), "1h"),
            (5,    now - datetime.timedelta(days=min(intraday_days, 7)), "5m"),
        ]

        total = 0
        for i, batch in enumerate(batches, 1):
            yf_tickers = [yf_t for _, yf_t, _ in batch]
            self.stdout.write(f"Batch {i}/{len(batches)}: {len(yf_tickers)} tickers...")
            candles: list[PriceCandle] = []

            for interval_minutes, start, iv_str in intervals:
                try:
                    df = yf.download(
                        yf_tickers,
                        start=start,
                        end=now,
                        interval=iv_str,
                        group_by="ticker",
                        auto_adjust=True,
                        progress=False,
                        threads=True,
                    )
                    if df.empty:
                        continue
                    for _, yf_ticker, asset in batch:
                        candles.extend(
                            self._candles_from_df(df, yf_ticker, asset, len(yf_tickers), interval_minutes)
                        )
                except Exception as exc:
                    self.stdout.write(self.style.WARNING(f"  {iv_str} failed: {exc}"))

            PriceCandle.objects.bulk_create(candles, ignore_conflicts=True)
            total += len(candles)
            self.stdout.write(f"  {len(candles)} candles saved.")

        self.stdout.write(self.style.SUCCESS(f"Total candles seeded: {total}"))

    def _candles_from_df(
        self,
        df: pd.DataFrame,
        yf_ticker: str,
        asset: Asset,
        n_tickers: int,
        interval_minutes: int,
    ) -> list[PriceCandle]:
        ticker_df = self._extract_ticker_df(df, yf_ticker, n_tickers)
        if ticker_df is None or ticker_df.empty:
            return []

        tz = get_asset_timezone(asset)
        candles: list[PriceCandle] = []

        for ts, row in ticker_df.iterrows():
            try:
                o, h, l, c = row["Open"], row["High"], row["Low"], row["Close"]
                if any(pd.isna(v) for v in (o, h, l, c)):
                    continue

                if interval_minutes == 1440:
                    day = ts.date() if hasattr(ts, "date") else ts
                    start_at = datetime.datetime.combine(
                        day, datetime.time.min, tzinfo=tz
                    ).astimezone(datetime.timezone.utc)
                else:
                    start_at = (
                        ts.astimezone(datetime.timezone.utc)
                        if getattr(ts, "tzinfo", None)
                        else ts.replace(tzinfo=datetime.timezone.utc)
                    )

                candles.append(PriceCandle(
                    asset=asset,
                    interval_minutes=interval_minutes,
                    start_at=start_at,
                    open_price=Decimal(str(round(float(o), 4))),
                    high_price=Decimal(str(round(float(h), 4))),
                    low_price=Decimal(str(round(float(l), 4))),
                    close_price=Decimal(str(round(float(c), 4))),
                    volume=int(row.get("Volume", 0) or 0),
                    source="LIVE",
                ))
            except Exception:
                continue

        return candles

    def _extract_ticker_df(
        self, df: pd.DataFrame, yf_ticker: str, n_tickers: int
    ) -> pd.DataFrame | None:
        if not isinstance(df.columns, pd.MultiIndex):
            return df if n_tickers == 1 else None
        level0 = df.columns.get_level_values(0).unique()
        if yf_ticker in level0:
            return df[yf_ticker]
        level1 = df.columns.get_level_values(1).unique()
        if yf_ticker in level1:
            return df.xs(yf_ticker, axis=1, level=1)
        return None

    @staticmethod
    def _chunks(lst: list, n: int):  # type: ignore[return]
        for i in range(0, len(lst), n):
            yield lst[i:i + n]
