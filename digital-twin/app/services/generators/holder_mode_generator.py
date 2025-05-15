from datetime import datetime

def get_rod_mode(timestamp: datetime) -> float:
    hour = timestamp.hour
    base_val = 1.0
    if 0 <= hour < 8:
        base_val = 1.0
    elif 8 <= hour < 16:
        base_val = 0.0
    else:
        base_val = 0.0

    return base_val

SENSOR_GENERATORS = {
    r"HolderMode[A-C]": get_rod_mode,
}
