from decimal import Decimal
from typing import Any

from django.core.management.base import BaseCommand

from market.models import Currency, FXRate
from market.api_access import get_currency_layer_api_data
from market.services.fx import update_currency_prices


class Command(BaseCommand):
	help = "Create currencies and seed FX rates for a fresh database."

	def handle(self, *args, **options): # type: ignore[no-untyped-def]
		currencies_data: list[dict[str, Any]] = [
			{"code": "GBP", "name": "British Pound Sterling", "is_base": True},
			{"code": "USD", "name": "US Dollar", "is_base": False},
			{"code": "EUR", "name": "Euro", "is_base": False},
		]

		currencies: dict[str, Currency] = {}
		for currency_data in currencies_data:
			currency, _ = Currency.objects.update_or_create(
				code=currency_data["code"],
				defaults={
					"name": currency_data["name"],
					"is_base": currency_data["is_base"],
				},
			)
			currencies[currency.code] = currency

		base_currency = Currency.objects.filter(is_base=True).first()
		if base_currency is None:
			base_currency = currencies.get("GBP")
			if base_currency is not None:
				base_currency.is_base = True
				base_currency.save(update_fields=["is_base"]) #type: ignore[no-untyped-call]

		api_data = get_currency_layer_api_data()
		if api_data and not api_data.get("skipped"):
			updated = update_currency_prices(api_data)
			self.stdout.write(self.style.SUCCESS(f"FX rates updated from API: {updated}"))
		else:
			dummy_rates: dict[str, Decimal] = {
				"GBP": Decimal("1.0"),
				"USD": Decimal("1.25"),
				"EUR": Decimal("1.10"),
			}
			if base_currency is None:
				self.stdout.write(self.style.WARNING("Base currency missing; skipping FX rates."))
				return

			for code, currency in currencies.items():
				rate = dummy_rates.get(code, Decimal("1.0"))
				FXRate.objects.update_or_create(
					base_currency=base_currency,
					target_currency=currency,
					defaults={"rate": rate},
				)
			self.stdout.write(self.style.SUCCESS("FX rates created using dummy values."))

		if base_currency is not None:
			FXRate.objects.update_or_create(
				base_currency=base_currency,
				target_currency=base_currency,
				defaults={"rate": Decimal("1.0")},
			)

		self.stdout.write(self.style.SUCCESS("Currencies setup complete."))
