import re
import os
import importlib
from typing import Dict, Optional, List, Tuple
import logging

from app.services import SensorGeneratorFunction

logger = logging.getLogger(__name__)

# Store regex pattern, compiled regex, and the generator function
GENERATOR_REGISTRY: List[Tuple[str, re.Pattern, SensorGeneratorFunction]] = []


def _load_generators():
    """
    Dynamically loads generator functions from modules in the 'generators' directory.
    Each generator module is expected to have a SENSOR_GENERATORS dictionary:
    { "regex_pattern": generator_function }
    """
    if GENERATOR_REGISTRY: # Avoid reloading if already loaded
        return

    logger.info("Loading sensor generators...")
    generators_path = os.path.join(os.path.dirname(__file__), "generators")
    for filename in os.listdir(generators_path):
        if filename.endswith("_generator.py") and filename != "__init__.py":
            module_name = f"app.services.generators.{filename[:-3]}"
            try:
                module = importlib.import_module(module_name)
                if hasattr(module, "SENSOR_GENERATORS") and isinstance(
                    module.SENSOR_GENERATORS, dict
                ):
                    for pattern_str, func in module.SENSOR_GENERATORS.items():
                        try:
                            compiled_pattern = re.compile(pattern_str)
                            GENERATOR_REGISTRY.append(
                                (pattern_str, compiled_pattern, func)
                            )
                            logger.info(
                                f"Registered generator for pattern '{pattern_str}' from {module_name}"
                            )
                        except re.error as e:
                            logger.error(
                                f"Invalid regex pattern '{pattern_str}' in {module_name}: {e}"
                            )
                else:
                    logger.warning(
                        f"Module {module_name} does not have a valid SENSOR_GENERATORS dict."
                    )
            except ImportError as e:
                logger.error(f"Failed to import generator module {module_name}: {e}")
    if not GENERATOR_REGISTRY:
        logger.warning("No sensor generators were loaded. Check generator modules.")


def get_generator_function(
    sensor_name: str,
) -> Optional[SensorGeneratorFunction]:
    """
    Finds a generator function that matches the sensor_name using regex.
    Returns the first match found.
    """
    if not GENERATOR_REGISTRY:
        _load_generators() # Ensure generators are loaded

    for pattern_str, compiled_pattern, func in GENERATOR_REGISTRY:
        logger.debug(f"Checking pattern '{pattern_str}' against sensor name '{sensor_name}'")
        if compiled_pattern.fullmatch(sensor_name): # Use fullmatch for exact pattern matching
            logger.debug(f"Sensor '{sensor_name}' matched pattern '{pattern_str}'")
            return func
    logger.warning(f"No generator found for sensor name: {sensor_name}")
    return None

# Call load_generators() on module import so it's ready.
# This is generally fine for non-huge numbers of generators.
# For very large systems, you might make it more lazy.
_load_generators()
