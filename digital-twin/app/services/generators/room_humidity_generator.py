from datetime import datetime
import random
import math

def generate_room_humidity(timestamp: datetime) -> float:
    """
    Generates room humidity with a daily sinusoidal pattern and noise.
    Humidity typically peaks in the cooler parts of the day (e.g., early morning)
    and drops during warmer parts (e.g., afternoon).
    """
    # Simulate a daily cycle: min humidity around 2 PM, max around 2 AM
    # Map hour to a 0-2*pi cycle, shifting so min is at 14:00
    hour_angle = ((timestamp.hour - 2 + 24) % 24) / 24.0 * 2 * math.pi # Shifted by 2 for min at 14:00

    # Base humidity range (e.g., 40% to 70%)
    min_humidity = 40.0
    max_humidity = 70.0
    amplitude = (max_humidity - min_humidity) / 2
    mean_humidity = min_humidity + amplitude

    # Cosine wave: peaks at angle 0 (2 AM), trough at pi (2 PM)
    base_humidity = mean_humidity - amplitude * math.cos(hour_angle)

    noise_range = 1.5  # +/- 1.5% noise
    noise = random.uniform(-noise_range, noise_range)
    final_humidity = round(base_humidity + noise, 2)

    return max(0.0, min(final_humidity, 100.0)) # Clamp between 0 and 100

SENSOR_GENERATORS = {
    r"room_([A-Za-z0-9]+_)?humidity": generate_room_humidity,
    r"env_sensor_hum": generate_room_humidity,
}

