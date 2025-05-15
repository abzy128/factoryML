from datetime import datetime
import random

def get_rod_release(timestamp: datetime) -> float:
    base_val = 0
    return base_val
    
def get_rod_raise(timestamp: datetime) -> float:
    raised = 1.0
    lowered = 0.0
    return raised if random.random() < 0.05 else lowered

SENSOR_GENERATORS = {
    r"UpperRingRelease[A-C]": get_rod_release,
    r"LowerRingRelease[A-C]": get_rod_release,
    r"UpperRingRaise[A-C]": get_rod_raise,
}
