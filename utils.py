# pylint: disable=all
import numpy as np

def create_sequences(values: np.ndarray, time_steps: int = 200) -> np.ndarray:
    """
    Creates sequences of values with a sliding window approach.

    This function takes a series of values and creates overlapping sequences
    of a specified length using a sliding window. Each sequence starts at
    consecutive positions in the input array.

    Args:
        values: Array-like object containing the input values to create sequences from
        time_steps: Int, the length of each sequence (default: 200)

    Returns:
        numpy.ndarray: A stacked array of sequences where each sequence has length time_steps.
        The shape will be (n_sequences, time_steps) where n_sequences = len(values) - time_steps + 1

    Example:
        >>> values = [1, 2, 3, 4, 5]
        >>> sequences = create_sequences(values, time_steps=3)
        >>> # Returns: array([[1, 2, 3],
        ...                   [2, 3, 4],
        ...                   [3, 4, 5]])
    """
    output = []
    for i in range(len(values) - time_steps + 1):
        output.append(values[i : (i + time_steps)])
    return np.stack(output)
