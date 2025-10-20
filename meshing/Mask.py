import numpy as np
from numpy import ndarray as NDArray
from typing import Optional, Callable, Tuple

from .utils import shift, boolean_function
from .BedMesh import BedMesh


class Mask:
    """
    Base Mask that builds grid coordinates. Children compute `self.mask`.
    Boundaries are exclusive.
    """

    def __init__(
        self,
        size_mm: float,
        grid_step_mm: float = 0.1,
        bottom_limit: float = 0.0,
        upper_limit: Optional[float] = None,
    ) -> None:
        self.size_mm = size_mm
        self.grid_step_mm = grid_step_mm
        upper_limit = upper_limit if upper_limit is not None else size_mm

        steps_count = int(round(size_mm / grid_step_mm)) + 1
        self._x_space = np.linspace(bottom_limit, upper_limit, steps_count)
        self._y_space = np.linspace(bottom_limit, upper_limit, steps_count)
        self._mesh = np.meshgrid(self._x_space, self._y_space, indexing="xy")
        # Children must set `self.mask` to a numpy array compatible with target shapes
        self.mask = np.zeros_like(self._mesh[0], dtype=float)

    def _shift_for(
        self,
        apply_position: Tuple[float, float] | NDArray,
        mask_anchor: Tuple[float, float] | NDArray,
    ) -> NDArray:
        """Compute the shifted mask for the given apply position and mask anchor.
        Note: shift() works with ij indexing, so (y, x) order for offsets.
        """
        x_displace = apply_position[0] - mask_anchor[0]
        y_displace = apply_position[1] - mask_anchor[1]
        return shift(
            self.mask,
            offset=(
                int(np.rint(y_displace / self.grid_step_mm)),
                int(np.rint(x_displace / self.grid_step_mm)),
            ),
        )

    def apply(
        self,
        target,
        apply_position: Tuple[float, float] | NDArray = (0.0, 0.0),
        mask_anchor: Tuple[float, float] | NDArray = (0.0, 0.0),
        time: float = 0.0,
    ) -> NDArray:
        """Child classes must override. Should return the resulting ndarray.
        If target is a BedMesh, it should update the appropriate field and return it.
        """
        raise NotImplementedError("Mask.apply must be implemented in child classes")


class SampleMask(Mask):
    """Boolean mask. Combines with logical OR onto target.
    - ndarray target: returns np.logical_or(target, shifted_mask)
    - BedMesh target: updates and returns target.bool_mesh

    The `function` must be a boolean mask generator compatible with `boolean_function` signature.
    """

    def __init__(
        self,
        size_mm: float,
        grid_step_mm: float = 0.1,
        bottom_limit: float = 0.0,
        upper_limit: Optional[float] = None,
        *,
        function: Callable = boolean_function,
        bl_corner: Tuple[float, float] | NDArray = (0.0, 0.0),
        x_size: Optional[float] = None,
        y_size: Optional[float] = None,
    ) -> None:
        super().__init__(
            size_mm=size_mm,
            grid_step_mm=grid_step_mm,
            bottom_limit=bottom_limit,
            upper_limit=upper_limit,
        )
        self.kind = "bool"
        # Default rectangle spans the given size if not provided
        xs = x_size if x_size is not None else size_mm
        ys = y_size if y_size is not None else size_mm
        # Persist rectangle parameters for downstream consumers (e.g., optimizer)
        self.bl_corner = np.array(bl_corner, dtype=float)
        self.x_size = float(xs)
        self.y_size = float(ys)
        # Build mask using the exact boolean function provided
        self.mask = function(self._mesh, self.bl_corner, xs, ys).astype(bool, copy=False)

    def apply(
        self,
        target,
        apply_position: Tuple[float, float] | NDArray = (0.0, 0.0),
        mask_anchor: Tuple[float, float] | NDArray = (0.0, 0.0),
        time: float = 0.0,
    ) -> NDArray:
        shifted_mask = self._shift_for(apply_position, mask_anchor).astype(bool, copy=False)

        if isinstance(target, np.ndarray):
            return np.logical_or(target.astype(bool, copy=False), shifted_mask)
        elif isinstance(target, BedMesh):
            result_arr = np.logical_or(target.bool_mesh, shifted_mask)
            target.bool_mesh = result_arr
            return result_arr
        else:
            raise TypeError(f"Unsupported target type: {type(target)!r}")


class SprayMask(Mask):
    """Numeric mask. Adds onto target, optionally scaled by time (>0).
    - ndarray target: returns target + shifted_mask*(time if time>0 else 1)
    - BedMesh target: updates and returns target.deposition_mesh

    The `function` must generate a numeric mask from the mesh, e.g., a Gaussian.
    Signature expected: function(mesh: Tuple[NDArray, NDArray]) -> NDArray
    """

    def __init__(
        self,
        size_mm: float,
        grid_step_mm: float = 0.1,
        bottom_limit: float = 0.0,
        upper_limit: Optional[float] = None,
        *,
        function: Callable | None = None,
    ) -> None:
        super().__init__(
            size_mm=size_mm,
            grid_step_mm=grid_step_mm,
            bottom_limit=bottom_limit,
            upper_limit=upper_limit,
        )
        self.kind = "numeric"
        if function is None:
            raise ValueError("SprayMask requires a numeric generator function (e.g., gaussian)")
        # Build mask using the exact numeric function provided
        self.mask = function(self._mesh).astype(float, copy=False)

    def apply(
        self,
        target,
        apply_position: Tuple[float, float] | NDArray = (0.0, 0.0),
        mask_anchor: Tuple[float, float] | NDArray = (0.0, 0.0),
        time: float = 0.0,
    ) -> NDArray:
        shifted_mask = self._shift_for(apply_position, mask_anchor)
        if time > 0:
            shifted_mask = shifted_mask * time

        if isinstance(target, np.ndarray):
            return target + shifted_mask
        elif isinstance(target, BedMesh):
            result_arr = target.deposition_mesh + shifted_mask
            target.deposition_mesh = result_arr
            return result_arr
        else:
            raise TypeError(f"Unsupported target type: {type(target)!r}")
