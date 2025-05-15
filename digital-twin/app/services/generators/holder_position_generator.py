from datetime import datetime
import random

def get_holder_position(timestamp: datetime) -> float:
    hour = timestamp.hour
    base_val = 200
    noise_range = 8

    if 0 <= hour < 2:
        base_val = 200
    elif 2 <= hour < 4:
        base_val = 195
    elif 4 <= hour < 8:
        base_val = 190
    elif 8 <= hour < 10:
        base_val = 185
    elif 10 <= hour < 12:
        base_val = 180
    elif 12 <= hour < 14:
        base_val = 175
    elif 14 <= hour < 16:
        base_val = 170
    elif 16 <= hour < 18:
        base_val = 165
    elif 18 <= hour < 20:
        base_val = 160
    elif 20 <= hour < 22:
        base_val = 155
    else:
        base_val = 150

    noise = random.uniform(-noise_range, noise_range)
    final_val = round(base_val + noise, 2)
    return final_val

SENSOR_GENERATORS = {
    r"CurrentHolderPosition[A-C]": get_holder_position,
}
