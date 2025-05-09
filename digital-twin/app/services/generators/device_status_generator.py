from datetime import datetime
import random

def generate_device_status(timestamp: datetime) -> int:
    """
    Generates a discrete device status (class value).
    Example: 0=OFF, 1=ON, 2=STANDBY, 3=ERROR
    - Mostly ON during working hours (8-18)
    - Occasionally STANDBY
    - Rare ERROR state
    - OFF otherwise
    """
    hour = timestamp.hour
    rand_val = random.random() # Value between 0.0 and 1.0

    if 8 <= hour < 18: # Working hours
        if rand_val < 0.01: # 1% chance of error
            return 3 # ERROR
        elif rand_val < 0.10: # 9% chance of standby (after error check)
            return 2 # STANDBY
        else: # 90% chance of ON
            return 1 # ON
    else: # Non-working hours
        if rand_val < 0.005: # 0.5% chance of error
            return 3 # ERROR
        elif rand_val < 0.7: # ~70% chance of OFF
            return 0 # OFF
        else: # ~30% chance of STANDBY
            return 2 # STANDBY

SENSOR_GENERATORS = {
    r"device_([A-Za-z0-9]+_)?status": generate_device_status,
    r"system_state_([0-9]+)": generate_device_status,
}

