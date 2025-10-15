import numpy as np
from numpy import ndarray as NDArray
from typing import Optional, Callable, Tuple
# from scipy.ndimage import shift  # too slow
from .utils import shift
from .utils import boolean_function, shift
from functools import singledispatchmethod
from .BedMesh import BedMesh

class Mask:
    # Kind specifies "bool" or "numeric" for the mask type
    # Rember boundaries are exclusive
    def __init__(self, size_mm: float, grid_step_mm: float = 0.1,
                 function: Callable = None, kind: str = "numeric", bottom_limit: float = 0, upper_limit: Optional[float] = None, ** fun_args) -> None:
        self.size_mm = size_mm
        self.kind = kind
        self.grid_step_mm = grid_step_mm
        upper_limit = upper_limit if upper_limit is not None else size_mm
        steps_count = int(round(size_mm / grid_step_mm)) + 1
        self._x_space = np.linspace(bottom_limit, upper_limit, steps_count)
        self._y_space = np.linspace(bottom_limit, upper_limit, steps_count)
        self.function = function
        self._mesh = np.meshgrid(
            self._x_space, self._y_space, indexing='xy'
        )
        self.specific_args = fun_args
        self.mask = self.function(self._mesh, **fun_args)  # Centered
        self._shifted_mask = self.mask

    @singledispatchmethod
    def apply(self, target, apply_position: Tuple[float, float] | NDArray = (
            0, 0), mask_anchor: Tuple[float, float] | NDArray = (0, 0), time: float = 0) -> NDArray:
        raise NotImplementedError("Unsupported target type")

    @apply.register
    def _(self, target: NDArray, apply_position: Tuple[float, float] | NDArray = (
            0, 0), mask_anchor: Tuple[float, float] | NDArray = (0, 0), time: float = 0) -> NDArray:
        x_displace = apply_position[0] - mask_anchor[0]
        y_displace = apply_position[1] - mask_anchor[1]
        # Shift function works with ij indexing, reverse xy
        shifted_mask = shift(
            self.mask,
            offset=(
                int(np.rint(y_displace / self.grid_step_mm)), int(np.rint(x_displace / self.grid_step_mm))
            )
        )

        if self.kind == "bool":
            result = np.logical_or(
                target, shifted_mask)
        else:
            shifted_mask = shifted_mask * time if time > 0 else shifted_mask
            result = target + shifted_mask
            pass
        return result

    @apply.register
    def _(self, target: "BedMesh", apply_position: Tuple[float, float] | NDArray = (
            0, 0), mask_anchor: Tuple[float, float] | NDArray = (0, 0), time: float = 0) -> NDArray:
        """Apply the mask to a target object with bool_mesh and grid_step_mm."""
        """Edits bed_mesh.deposition_mesh directly."""
        x_displace = apply_position[0] - mask_anchor[0]
        y_displace = apply_position[1] - mask_anchor[1]
        shifted_mask = shift(
            self.mask,
            offset=(
                int(np.rint(y_displace / self.grid_step_mm)), int(np.rint(x_displace / self.grid_step_mm))
            )
        )
        if self.kind == "bool":
            result_arr = np.logical_or(target.bool_mesh, shifted_mask)
            target.bool_mesh = result_arr
        else:
            shifted_mask = shifted_mask * time if time > 0 else shifted_mask
            target_arr = target.deposition_mesh
            result_arr = target_arr + shifted_mask
            target.deposition_mesh = result_arr
        return result_arr
