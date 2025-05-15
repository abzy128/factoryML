from datetime import datetime
import random

def get_rod_high_voltage(timestamp: datetime) -> float:
    hour = timestamp.hour
    base_val = 185
    noise_range = 1

    if 0 <= hour < 8:
        base_val = 184
    elif 8 <= hour < 16:
        base_val = 186
    else:
        base_val = 185

    noise = random.uniform(-noise_range, noise_range)
    final_val = round(base_val + noise, 2)
    return final_val

def get_rod_voltage_step(timestamp: datetime) -> float:
    hour = timestamp.hour
    base_val = 35
    noise_range = 1

    if 0 <= hour < 8:
        base_val = 35
    elif 8 <= hour < 16:
        base_val = 37
    else:
        base_val = 39

    noise = random.uniform(-noise_range, noise_range)
    final_val = round(base_val + noise, 2)
    return final_val

SENSOR_GENERATORS = {
    r"HighVoltage[A-C]": get_rod_high_voltage,
    r"VoltageStep[A-C]": get_rod_voltage_step,
}
