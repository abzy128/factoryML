from datetime import datetime
import random

def generate_gas_pressure_under_furnace_a(timestamp: datetime) -> float:
    hour = timestamp.hour
    base_val = -100.0
    noise_range = 10

    if 0 <= hour < 8:
        base_val = -80.0
    elif 8 <= hour < 16:
        base_val = -100.0
    else:
        base_val = -100.0

    noise = random.uniform(-noise_range, noise_range)
    final_val = round(base_val + noise, 2)

    return final_val

def generate_gas_pressure_under_furnace_b(timestamp: datetime) -> float:
    hour = timestamp.hour
    base_val = -95.0
    noise_range = 9

    if 0 <= hour < 8:
        base_val = -76.0
    elif 8 <= hour < 16:
        base_val = -95.0
    else:
        base_val = -95.0

    noise = random.uniform(-noise_range, noise_range)
    final_val = round(base_val + noise, 2)

    return final_val

def generate_gas_pressure_under_furnace_c(timestamp: datetime) -> float:
    hour = timestamp.hour
    base_val = -98.0
    noise_range = 9

    if 0 <= hour < 8:
        base_val = -78.0
    elif 8 <= hour < 16:
        base_val = -98.0
    else:
        base_val = -98.0

    noise = random.uniform(-noise_range, noise_range)
    final_val = round(base_val + noise, 2)

    return final_val

SENSOR_GENERATORS = {
    r"GasPressureUnderFurnaceA": generate_gas_pressure_under_furnace_a,
    r"GasPressureUnderFurnaceB": generate_gas_pressure_under_furnace_b,
    r"GasPressureUnderFurnaceC": generate_gas_pressure_under_furnace_c,
}
