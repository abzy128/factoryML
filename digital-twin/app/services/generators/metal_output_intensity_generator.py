from datetime import datetime
import random

def get_metal_output_intensity(timestamp: datetime) -> float:
    hour = timestamp.hour
    base_val = 0.0
    noise_range = 0.5

    if 0 <= hour < 8:
        base_val = 0.5
    elif 8 <= hour < 16:
        base_val = 22
    else:
        base_val = 30

    noise = random.uniform(-noise_range, noise_range)
    final_temp = round(base_val + noise, 2)
    return max(0.0, final_temp)


SENSOR_GENERATORS = {
    r"MetalOutputIntensity": get_metal_output_intensity,
}
