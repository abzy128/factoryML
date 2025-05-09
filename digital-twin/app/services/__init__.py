from typing import Callable, Union
from datetime import datetime

# Define a type alias for our generator functions
# A generator function takes a datetime object (current timestamp)
# and returns a float or an int.
SensorGeneratorFunction = Callable[[datetime], Union[float, int, str]]

# This __init__.py can also be used to auto-discover generators later if needed,
# but for now, we'll explicitly import them in sensor_registry.py.
