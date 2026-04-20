import os
from decimal import Decimal
# Application specific constants

# Application specific settings
STARTING_BALANCE = Decimal("100000.00") # in server base currency
MARKET_DATA_MODE = os.getenv("MARKET_DATA_MODE", "SIMULATION").upper()  # live or simulation


MARKET_TICK_INTERVAL_MINUTES = 5  # Interval for market ticks (5 min)
FX_RATES_UPDATE_INTERVAL_MINUTES = 8 * 60  # Interval for FX rates updates (8hrs)

# Order expiry
ORDER_EXPIRY_DAYS = 30  # Pending orders older than this are expired

# SImulation parameters
SIMULATION_INITIAL_PRICE_RANGE = (50.0, 250.0)  # Initial price range Note: probably don't need this if seeding with real data
SIMULATION_MU = 0.06  # Annual Drift coefficient
SIMULATION_SIGMA = 0.25  # Annual Volatility coefficient


# WARNING: Must match frontend/src/lib/utils.ts TRADING_FEE_RATE
TRADING_FEE_PERCENTAGE = Decimal('0.001')
