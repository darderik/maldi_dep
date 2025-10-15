import numpy as np
from numpy import ndarray as NDArray
from numpy.typing import ArrayLike
from typing import Optional, Callable, Tuple



def boolean_function(mesh: Tuple[NDArray, NDArray], corner1: NDArray |
                     Tuple[float, float], x_size: float = 1.0, y_size: float = 1.0) -> NDArray:
    """Generates a boolean mask based on a threshold."""
    x1c, y1c, x2c, y2c = corner1[0], corner1[1], corner1[0] + x_size, corner1[1] + y_size

    x, y = mesh
    # TODO Float issues on comparison
    return np.logical_and(np.logical_and(x >= x1c, x <= x2c), np.logical_and(y >= y1c, y <= y2c))


def shift(array: NDArray, offset: ArrayLike, constant_values=0):
    """Returns copy of array shifted by offset, with fill using constant."""
    """Author: Hugues"""
    array = np.asarray(array)
    offset = np.atleast_1d(offset)
    assert len(offset) == array.ndim
    new_array = np.empty_like(array)

    def slice1(o):
        return slice(o, None) if o >= 0 else slice(0, o)

    new_array[tuple(slice1(o) for o in offset)] = (
        array[tuple(slice1(-o) for o in offset)])

    for axis, o in enumerate(offset):
        new_array[(slice(None),) * axis +
                  (slice(0, o) if o >= 0 else slice(o, None),)] = constant_values

    return new_array
