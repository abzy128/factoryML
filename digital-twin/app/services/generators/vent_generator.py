from datetime import datetime
import random

def get_ventialation_valve_a(timestamp: datetime) -> float:
    base_val = 0
    return base_val

def get_ventialation_valve_b(timestamp: datetime) -> float:
    hour = timestamp.hour
    base_val = 200
    noise_range = 5

    if 0 <= hour < 8:
        noise_range = 6
    elif 8 <= hour < 16:
        noise_range = 4
    else:
        noise_range = 6

    noise = random.uniform(-noise_range, noise_range)
    final_val = round(base_val + noise, 2)
    return max(200.0, final_val)

def get_ventialation_valve_c(timestamp: datetime) -> float:
    hour = timestamp.hour
    base_val = 9.0
    noise_range = 0.5

    if 0 <= hour < 8:
        base_val = 9.1
    elif 8 <= hour < 16:
        base_val = 9.0
    else:
        base_val = 9.0

    noise = random.uniform(-noise_range, noise_range)
    final_val = round(base_val + noise, 2)
    return final_val

def get_air_temperature_a(timestamp: datetime) -> float:
    hour = timestamp.hour
    base_val = 90
    noise_range = 5

    if 0 <= hour < 8:
        noise_range = 90
    elif 8 <= hour < 16:
        noise_range = 120
    else:
        noise_range = 80

    noise = random.uniform(-noise_range, noise_range)
    final_val = round(base_val + noise, 2)
    return min(200.0, final_val)

def get_air_temperature_b(timestamp: datetime) -> float:
    hour = timestamp.hour
    base_val = 200
    noise_range = 10

    if 0 <= hour < 8:
        base_val = 200
    elif 8 <= hour < 16:
        base_val = 170
    else:
        base_val = 185

    noise = random.uniform(-noise_range, noise_range)
    final_val = round(base_val + noise, 2)
    return min(200.0, final_val)

def get_air_temperature_c(timestamp: datetime) -> float:
    hour = timestamp.hour
    base_val = 70
    noise_range = 5

    if 0 <= hour < 8:
        base_val = 70
    elif 8 <= hour < 16:
        base_val = 60
    else:
        base_val = 64

    noise = random.uniform(-noise_range, noise_range)
    final_val = round(base_val + noise, 2)
    return final_val


SENSOR_GENERATORS = {
    r"VentialtionValveForMantelA": get_ventialation_valve_a,
    r"VentialtionValveForMantelB": get_ventialation_valve_b,
    r"VentialtionValveForMantelC": get_ventialation_valve_c,
    r"AirTemperatureMantelA": get_air_temperature_a,
    r"AirTemperatureMantelB": get_air_temperature_b,
    r"AirTemperatureMantelC": get_air_temperature_c,
}
