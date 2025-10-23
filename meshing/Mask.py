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
        Use sub-pixel shifts (floats) to avoid banding artifacts.
        """
        # Default: global shift (used by SampleMask)
        x_cells = (apply_position[0] - mask_anchor[0]) / self.grid_step_mm
        y_cells = (apply_position[1] - mask_anchor[1]) / self.grid_step_mm
        return shift(self.mask, offset=(y_cells, x_cells), constant_values=0.0, order=1, prefilter=False)

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
    Assumes this mask is a small, centered kernel built in Nozzle.__init__.
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
        # Build small kernel from provided function on the local mesh
        self.mask = function(self._mesh).astype(float, copy=False)
        # Precompute kernel radius in cells for window slicing
        self._radius_cells = (self.mask.shape[0] - 1) // 2

    def apply(
        self,
        target,
        apply_position: Tuple[float, float] | NDArray = (0.0, 0.0),
        mask_anchor: Tuple[float, float] | NDArray = (0.0, 0.0),
        time: float = 0.0,
    ) -> NDArray:
        # Shift only the small kernel by sub-pixel (fractional) offset
        step = self.grid_step_mm
        ux = float(apply_position[0] - mask_anchor[0]) / step
        uy = float(apply_position[1] - mask_anchor[1]) / step
        jx = int(np.floor(ux))
        jy = int(np.floor(uy))
        fx = ux - jx
        fy = uy - jy
        # Sub-pixel shift (y, x) and scale by time if provided
        shifted_tile = shift(self.mask, offset=(fy, fx), constant_values=0.0, order=1, prefilter=False)
        if time > 0:
            shifted_tile = shifted_tile * time

        if isinstance(target, np.ndarray):
            # Global ndarray target (rare here) — add centered around (jy, jx)
            r = self._radius_cells
            H, W = target.shape
            bed_y0 = max(0, jy - r)
            bed_y1 = min(H, jy + r + 1)
            bed_x0 = max(0, jx - r)
            bed_x1 = min(W, jx + r + 1)
            ker_y0 = r - (jy - bed_y0)
            ker_y1 = ker_y0 + (bed_y1 - bed_y0)
            ker_x0 = r - (jx - bed_x0)
            ker_x1 = ker_x0 + (bed_x1 - bed_x0)
            target[bed_y0:bed_y1, bed_x0:bed_x1] += shifted_tile[ker_y0:ker_y1, ker_x0:ker_x1]
            return target
        elif isinstance(target, BedMesh):
            # Windowed in-place add into the bed deposition mesh
            r = self._radius_cells
            H, W = target.deposition_mesh.shape
            bed_y0 = max(0, jy - r)
            bed_y1 = min(H, jy + r + 1)
            bed_x0 = max(0, jx - r)
            bed_x1 = min(W, jx + r + 1)
            ker_y0 = r - (jy - bed_y0)
            ker_y1 = ker_y0 + (bed_y1 - bed_y0)
            ker_x0 = r - (jx - bed_x0)
            ker_x1 = ker_x0 + (bed_x1 - bed_x0)
            target.deposition_mesh[bed_y0:bed_y1, bed_x0:bed_x1] += shifted_tile[ker_y0:ker_y1, ker_x0:ker_x1]
            return target.deposition_mesh
        else:
            raise TypeError(f"Unsupported target type: {type(target)!r}")
