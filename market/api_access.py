import os
from typing import Any

import requests
from market.models import Currency, FXRate

def get_currency_layer_api_data() -> dict[str, Any] | None:

    """Fetches live currency exchange rates from Currency Layer API."""

    base_url = "http://api.currencylayer.com/live"
    api_key = os.getenv('CURRENCY_LAYER_API_KEY')
    if not api_key:
        print("Currency Layer API key not found in environment variables.")
        return None

    base_currency = Currency.objects.get(is_base=True)
    currencies = Currency.objects.exclude(code=base_currency.code).values_list('code', flat=True)
    if not currencies:
        return {"skipped": True, "reason": "no_currencies"}

    params: dict[str, str | int] = {
        'access_key': api_key,
        'currencies': ','.join(currencies),
        'source': base_currency.code,
        'format': 1
    }
    response = requests.get(base_url, params=params)

    if response.status_code != 200:
        print(f"Failed to fetch data from Currency Layer API. Status code: {response.status_code}")
        return None
    
    data: dict[str, Any] = response.json()
    if not data.get('success'):
        print(f"Currency Layer API error: {data.get('error')}")
        return None
    else:
        return data

# TODO: get stock market data from another API