from datetime import datetime
import random

def generate_power(timestamp: datetime) -> float:
    rand_val = (random.random() * 2) - 1
    return 28 + (rand_val * 2)

def generate_power_setpoint(timestamp: datetime) -> float:
    return 30

def generate_rod_power(timestamp: datetime) -> float:
    return generate_power(timestamp) * 0.33

SENSOR_GENERATORS = {
    r"ActivePower": generate_power,
    r"ReactivePower": generate_power,
    r"Power[A-C]": generate_rod_power,
    r"PowerSetpoint": generate_power_setpoint,
}
