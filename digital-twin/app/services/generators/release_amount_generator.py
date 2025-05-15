from datetime import datetime
import random

def generate_release_amount_a(timestamp: datetime) -> float:
    hour = timestamp.hour
    base_val = 200.0
    noise_range = 30

    if 0 <= hour < 3 or 6 <= hour < 9:
        base_val = 200.0
    elif 3 <= hour < 6 or 15 <= hour < 24:
        base_val = 100.0
    elif 9 <= hour < 12:
        base_val = 300.0
    elif 12 <= hour < 15:
        base_val = 380.0
    else:
        base_val = 170

    noise = random.uniform(-noise_range, noise_range)
    final_temp = round(base_val + noise, 2)
    return max(0.0, final_temp)

def generate_release_amount_b(timestamp: datetime) -> float:
    hour = timestamp.hour
    base_val = 200.0
    noise_range = 30

    if 0 <= hour < 3 or 6 <= hour < 9:
        base_val = 190.0
    elif 3 <= hour < 6 or 15 <= hour < 24:
        base_val = 95.0
    elif 9 <= hour < 12:
        base_val = 295.0
    elif 12 <= hour < 15:
        base_val = 379.0
    else:
        base_val = 175

    noise = random.uniform(-noise_range, noise_range)
    final_temp = round(base_val + noise, 2)
    return max(0.0, final_temp)

def generate_release_amount_c(timestamp: datetime) -> float:
    hour = timestamp.hour
    base_val = 200.0
    noise_range = 30

    if 0 <= hour < 3 or 6 <= hour < 9:
        base_val = 189.0
    elif 3 <= hour < 6 or 15 <= hour < 24:
        base_val = 99.0
    elif 9 <= hour < 12:
        base_val = 280.0
    elif 12 <= hour < 15:
        base_val = 370.0
    else:
        base_val = 160

    noise = random.uniform(-noise_range, noise_range)
    final_temp = round(base_val + noise, 2)
    return max(0.0, final_temp)

SENSOR_GENERATORS = {
    r"ReleaseAmountA": generate_release_amount_a,
    r"ReleaseAmountB": generate_release_amount_b,
    r"ReleaseAmountC": generate_release_amount_c,
}
