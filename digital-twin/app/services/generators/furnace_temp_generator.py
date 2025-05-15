from datetime import datetime
import random

def generate_furnace_temperature(timestamp: datetime) -> float:
    hour = timestamp.hour
    base_val = 680
    noise_range = 3

    if 0 <= hour < 8:
        base_val = 670
    elif 8 <= hour < 16:
        base_val = 680
    else:
        base_val = 685

    noise = random.uniform(-noise_range, noise_range)
    final_val = round(base_val + noise, 2)

    return final_val

def generate_furnace_bath_temperature(timestamp: datetime) -> float:
    return generate_furnace_temperature(timestamp) * 1.2

SENSOR_GENERATORS = {
    r"FurnacePodTemparature": generate_furnace_temperature,
    r"FurnaceBathTemperature": generate_furnace_bath_temperature,
}
