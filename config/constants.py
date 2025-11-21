import os
# Application specific constants

CURRENCY_SYMBOLS = {
    "GBP": "£",
    "USD": "$",
    "EUR": "€",
}

# Application specific settings
STARTING_BALANCE = 100_000.00 #gbp
MARKET_DATA_MODE = os.getenv("MARKET_DATA_MODE", "SIMULATION").upper()  # live or simulation

# # Check that previous price history mode is valid
# if PriceHistory.objects.first() is not None:
#     if PriceHistory.objects.latest().source.upper() == "SIMULATION" and MARKET_DATA_MODE == "LIVE":
#         decision = input("You are switching to Live Mode. Existing simulated data will be preserved but will no longer be used for assets that have live data. Do you want to clear all simulated data before switching? (Y/N)")
#         if decision.strip().upper() == "Y":
#             print("Clearing simulated price history data...")
#             PriceHistory.objects.filter(source="SIMULATION").delete()



STOCKS_UPDATE_INTERVAL_SECONDS = 60  # Interval for market data updates

# SImulation parameters
SIMULATION_INITIAL_PRICE_RANGE = (50.0, 250.0)  # Initial price range
SIMULATION_MU = 0.08  # Annual Drift coefficient
SIMULATION_SIGMA = 0.20  # Annual Volatility coefficient


