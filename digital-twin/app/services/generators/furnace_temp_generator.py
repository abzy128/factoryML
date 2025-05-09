from datetime import datetime
import random

def generate_furnace_temperature(timestamp: datetime) -> float:
    """
    Generates furnace temperature based on time of day with noise.
    - 00:00 - 07:59: Idle temperature (e.g., 400-450)
    - 08:00 - 15:59: Peak operation (e.g., 540-560)
    - 16:00 - 19:59: Reduced operation (e.g., 490-510)
    - 20:00 - 23:59: Cooling down/Idle (e.g., 400-450)
    """
    hour = timestamp.hour
    base_temp = 0.0
    noise_range = 2.5  # +/- 2.5 degrees noise

    if 0 <= hour < 8:
        base_temp = 425.0
    elif 8 <= hour < 16:
        base_temp = 550.0
    elif 16 <= hour < 20:
        base_temp = 500.0
    else: # 20 <= hour < 24
        base_temp = 425.0

    # Add some progression within the hour for slight variability
    minute_factor = (timestamp.minute / 59.0) * 5 # Small drift within the hour
    if 8 <= hour < 16: # During peak, maybe slight increase
        base_temp += minute_factor
    elif 16 <= hour < 20: # During reduction, maybe slight decrease
        base_temp -= minute_factor


    noise = random.uniform(-noise_range, noise_range)
    final_temp = round(base_temp + noise, 2)

    # Ensure temperature stays within overall bounds
    return max(380.0, min(final_temp, 620.0))

# To make it discoverable by the registry
SENSOR_GENERATORS = {
    # Regex: Matches "furnace" followed by anything, then "temperature"
    r"furnace.*temperature": generate_furnace_temperature,
    r"oven_[A-Za-z0-9]+_temp": generate_furnace_temperature, # Another example
}

