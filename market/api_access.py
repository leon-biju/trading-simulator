import os
import requests
from market.models import CurrencyAsset, Currency

def get_currency_layer_api_data() -> dict | None:

    """Fetches live currency exchange rates from Currency Layer API."""

    base_url = "http://api.currencylayer.com/live"
    api_key = os.getenv('CURRENCY_LAYER_API_KEY')
    if not api_key:
        print("Currency Layer API key not found in environment variables.")
        return None
    
    currencies = CurrencyAsset.objects.values_list('symbol', flat=True)
    params = {
        'access_key': api_key,
        'currencies': ','.join(currencies),
        'source': Currency.objects.get(is_base=True).code,
        'format': 1
    }
    response = requests.get(base_url, params=params)

    if response.status_code != 200:
        print(f"Failed to fetch data from Currency Layer API. Status code: {response.status_code}")
        return None
    
    data = response.json()
    if not data.get('success'):
        print(f"Currency Layer API error: {data.get('error')}")
        return None
    else:
        return data