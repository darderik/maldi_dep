import numpy as np
from numpy import ndarray as NDArray
from numpy.typing import ArrayLike
from typing import Optional, Callable, Tuple, Iterable, List



def boolean_function(mesh: Tuple[NDArray, NDArray], corner1: NDArray |
                     Tuple[float, float], x_size: float = 1.0, y_size: float = 1.0) -> NDArray:
    """Generates a boolean mask based on a threshold."""
    x1c, y1c, x2c, y2c = corner1[0], corner1[1], corner1[0] + x_size, corner1[1] + y_size

    x, y = mesh
    # Inclusive on bottom-left, exclusive on top-right to avoid boundary overlaps between adjacent samples
    # TODO Float issues on comparison
    return np.logical_and(np.logical_and(x >= x1c, x < x2c), np.logical_and(y >= y1c, y < y2c))


def shift(array: NDArray, offset: ArrayLike, constant_values: float = 0.0, order: int = 1, mode: str = 'constant', prefilter: bool = False) -> NDArray:
    """
    Sub-pixel array shift using scipy.ndimage.shift.

    Parameters
    - array: input ndarray.
    - offset: (dy, dx) in pixel units. Supports floats for sub-pixel shifts.
    - constant_values: value used to fill introduced areas (mapped to cval).
    - order: interpolation order (0=nearest, 1=bilinear, 3=cubic, ...).
    - mode: how to handle borders (default 'constant').
    - prefilter: passed through to ndimage.shift (relevant for order>1). Default False for speed with order=1.

    Returns shifted copy of `array`.
    """
    from scipy.ndimage import shift as ndi_shift
    arr = np.asarray(array)
    off = np.asarray(offset, dtype=float).reshape(-1)
    assert off.size == arr.ndim, "offset must have one value per array dimension"
    return ndi_shift(arr, shift=tuple(off.tolist()), order=order, mode=mode, cval=float(constant_values), prefilter=prefilter)


def shift_batch(array: NDArray, offsets: Iterable[Tuple[float, float]], constant_values: float = 0.0, order: int = 1, mode: str = 'constant', prefilter: bool = False) -> List[NDArray]:
    """
    Convenience to compute many shifted versions of the same array.
    Useful for precomputing a cache for common sub-pixel offsets.
    """
    return [shift(array, off, constant_values=constant_values, order=order, mode=mode, prefilter=prefilter) for off in offsets]
