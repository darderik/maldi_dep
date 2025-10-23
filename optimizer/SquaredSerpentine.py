# This optimizer aims to create a cornered serpentine on each sample area
from meshing import BedMesh, Mask
from typing import List, Tuple
from numpy import array as Array
from numpy import ndarray as NDArray
from numpy.typing import ArrayLike
from graphing import plot_x_y_points
import numpy as np
from simulation import Movement


class SquaredSerpentine:
    def __init__(self, bm: BedMesh, bool_mask: Mask, margin: float = 4, x_amnt: int = 2, stride: float = 1,
                 speed: float = 5.0, max_speed: float = 100.0, passes: int = 1, alternate_offset: bool = False) -> None:
        # Elaborate corners of bool mask
        # Only a single boolean mask for each squared serpentine, no simultaneous masks
        self.mask = bool_mask
        self.bm = bm
        self.margin: float = margin
        self.x_amnt = x_amnt
        self.stride = stride
        self.movements: List[Movement] = []
        self.passes = passes
        self.speed = speed
        self.max_speed = max_speed
        self.alternate_offset = alternate_offset
        self._compute_serpentines()
    def get_stride(self) -> float:
        """Get the current stride value."""
        return self.stride
    def set_stride(self, stride: float) -> None:
        """Set a new stride and recompute serpentines."""
        self.stride = stride
        self._compute_serpentines()

    def set_margin(self, margin: float) -> None:
        """Set a new margin and recompute serpentines."""
        self.margin = margin
        self._compute_serpentines()

    def set_stride_and_margin(self, stride: float, margin: float) -> None:
        """Set both stride and margin and recompute serpentines."""
        self.stride = stride
        self.margin = margin
        self._compute_serpentines()

    def _compute_serpentines(self) -> None:
        """Compute the serpentine paths based on current margin and stride.
        The serpentine movement zone is the mask bounding box expanded by `margin` in all directions,
        then clamped to the overall bed extents [0, size_mm].
        """
        self.movements = []
        # Retrieve mask bbox from SampleMask attributes if available
        bl_corner = getattr(self.mask, 'bl_corner', None)
        x_size_attr = getattr(self.mask, 'x_size', None)
        y_size_attr = getattr(self.mask, 'y_size', None)
        if bl_corner is None or x_size_attr is None or y_size_attr is None:
            # Cannot compute without bbox information
            return
        # Mask Data (bounding box in mm)
        corner1: NDArray = Array(bl_corner)  # (x_min, y_min)
        x_size: float = float(x_size_attr)
        y_size: float = float(y_size_attr)
        x_min = float(corner1[0])
        y_min = float(corner1[1])
        x_max = x_min + x_size
        y_max = y_min + y_size

        # Expand bbox by margin (sprayer movement area) and clamp to bed only
        bm_size = getattr(self.bm, "size_mm", None)
        x_left = x_min - self.margin
        x_right = x_max + self.margin
        y_bottom = y_min - self.margin
        y_top = y_max + self.margin

        if bm_size is not None:
            x_left = max(0.0, x_left)
            y_bottom = max(0.0, y_bottom)
            x_right = min(bm_size, x_right)
            y_top = min(bm_size, y_top)

        # If the expanded-and-clamped interval collapses, fall back to bbox clamped to bed
        x_min_c = max(0.0, x_min) if bm_size is not None else x_min
        y_min_c = max(0.0, y_min) if bm_size is not None else y_min
        x_max_c = min(bm_size, x_max) if bm_size is not None else x_max
        y_max_c = min(bm_size, y_max) if bm_size is not None else y_max
        if x_right <= x_left:
            x_left, x_right = x_min_c, x_max_c
        if y_top <= y_bottom:
            y_bottom, y_top = y_min_c, y_max_c

        # If still invalid (e.g., bbox fully outside bed), skip
        if not (x_right > x_left and y_top > y_bottom):
            return

        # Base arrays (stay within clamped movement zone)
        x_source: NDArray = np.array(
            np.linspace(x_left, x_right, max(2, int(self.x_amnt))), dtype=float
        )

        height = abs(y_top - y_bottom)
        y_amnt = max(2, int(height / max(self.stride, 1e-9)) + 1)
        y_source: NDArray = np.linspace(y_top, y_bottom, y_amnt)

        # Create final y_array adapting to x_source: one horizontal sweep per y
        y_final: NDArray = np.repeat(y_source, x_source.shape[0])

        # Populate x (serpentine: alternate direction each row)
        x_final: NDArray = np.array([], dtype=float)
        for count in range(0, len(y_source)):
            if (count % 2 == 0):
                x_final = np.concatenate((x_final, x_source))
            else:
                x_final = np.concatenate((x_final, np.flip(x_source)))

        # Assemble, ensure equal length
        length: int = min(x_final.shape[0], y_final.shape[0])
        x_final = x_final[0:length]
        y_final = y_final[0:length]
        points = np.vstack((x_final, y_final))
        # Generate Movement list
        cur_movements: List[Movement] = []
        n = points.shape[1]
        for pass_num in range(self.passes):
            # If even pass, follow normal order, else reverse order
            is_even_pass: bool = (pass_num % 2 == 0)
            if is_even_pass:
                order = range(n)
            else:
                order = range(n - 1, -1, -1)
            y_ofs = 0.0
            for i in order:
                if not is_even_pass and self.alternate_offset:
                    y_ofs = self.stride / 2.0
                x = float(points[0, i])
                y = float(points[1, i]) + y_ofs
                mv = Movement(x, y, speed=self.speed)
                cur_movements.append(mv)

        self.movements = cur_movements

    def draw(self, ax=None):
        """Draw the serpentine paths on the provided axis or create a new one."""
        created_ax = False
        if ax is None:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots()
            created_ax = True
        x = [movement.x for movement in self.movements]
        y = [movement.y for movement in self.movements]
        ax.quiver(x[:-1], y[:-1], np.diff(x), np.diff(y), angles='xy', scale_units='xy', scale=1)
        ax.set_xlim(0, self.bm.size_mm)
        ax.set_ylim(0, self.bm.size_mm)
        ax.grid(True)
        if created_ax:
            import matplotlib.pyplot as plt
            plt.show()
