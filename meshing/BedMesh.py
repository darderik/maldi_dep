import numpy as np
from numpy import ndarray as NDArray
from numpy.typing import ArrayLike
from typing import Optional, Callable, Tuple, List
import scipy.interpolate as interp
from functools import singledispatch
from .utils import boolean_function
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from scipy.ndimage import label as ndimage_label, find_objects


class BedMesh:
    def __init__(self, size_mm: float, grid_step_mm: float, spray_function: Optional[Callable] = None):
        """
        Initialize the BedMesh object.

        Args:
            size_mm (float): The size of the mesh in millimeters.
            grid_step_mm (float): The step size of the grid in millimeters.
        """
        steps_count = int(round(size_mm / grid_step_mm)) + 1
        self.steps_count = steps_count
        self._x_space = np.linspace(0, size_mm, steps_count)
        self._y_space = np.linspace(0, size_mm, steps_count)
        temp_mesh: NDArray = np.zeros((steps_count, steps_count), dtype=float)
        self.deposition_mesh: NDArray = temp_mesh
        self.bool_mesh = np.zeros_like(temp_mesh, dtype=bool)
        self.size_mm = size_mm
        self.grid_step_mm = grid_step_mm
        self._bool_masks = []
        self.spray_function = spray_function
        self.init_nozzle()

    def get_point(self, x: float, y: float, method: str = "cubic"):
        """
        Get the value at a specific point in the mesh.

        Args:
            x (float): The x-coordinate of the point.
            y (float): The y-coordinate of the point.
            method (str): The interpolation method to use (default is "cubic").

        Returns:
            Optional[float]: The interpolated value at the specified point, or None if out of bounds.
        """
        interpolator = interp.RegularGridInterpolator(
            (self._x_space, self._y_space), self.deposition_mesh, bounds_error=False, method=method
        )
        result = interpolator([x, y])
        return result

    def add_bool_mask(self, points: List[List[float]], shape: str = "rectangle", ) :
        """
        Add a boolean mask to the bed mesh.

        Args:
            points (ArrayLike): An array of points defining the mask. For rectangles, this should be an array of (x_min, x_max, y_min, y_max).
            shape (str): The shape of the mask (default is "rectangle").

        Raises:
            ValueError: If the shape is not recognized.
        """
        from .Mask import SampleMask
        if shape == "rectangle":
            points_arr = np.array(points)
            for sample in points_arr:
                corner1 = (sample[0], sample[2])
                x_size = sample[1] - sample[0]
                y_size = sample[3] - sample[2]
                mask = SampleMask(
                    size_mm=self.size_mm,
                    grid_step_mm=self.grid_step_mm,
                    bl_corner=corner1,
                    x_size=x_size,
                    y_size=y_size,
                )
                mask.apply(self, apply_position=(0, 0), mask_anchor=(0, 0))
                self._bool_masks.append(mask)
                return mask
                
        else:
            raise ValueError(f"Unknown shape: {shape}")  # TODO More shapes

    def init_nozzle(self):
        """
        Initialize the nozzle for this bed mesh.

        This method sets up the nozzle object associated with the bed mesh.
        """
        from .Nozzle import Nozzle
        self._nozzle = Nozzle(owner_bed=self, nozzle_function=self.spray_function)

    def get_std_deviation(self, overall_dev: bool = False) -> List[float]:
        """
        Calculate the standard deviation of the deposition mesh.

        Returns:
            float: The standard deviation of the deposition mesh values within the boolean mask.
        """
        result = ndimage_label(self.bool_mesh)
        
        if not overall_dev:
            labeled_bool, num_features = result if isinstance(result, tuple) else (result, None)
            depositions_masks = []
            for i in range(1, (num_features or 0) + 1):
                depositions_masks.append(self.deposition_mesh[labeled_bool == i])
            devs = [float(np.std(dm)) for dm in depositions_masks if dm.size > 0]
        else:
            devs = [float(np.std(self.deposition_mesh[self.bool_mesh]))]
        
        return devs

    def plot(self, keyword: str = "deposition", ax=None) -> None:
        """
        Plot the deposition mesh or other specified data.

        Args:
            keyword (str): The type of data to plot (default is "deposition").
            ax: Optional axis object to plot on. If None, a new figure and axis will be created.

        Raises:
            ValueError: If the keyword is not recognized.
        """

        def _plot_bounding_boxes(ax, labeled, step):
            for sl in find_objects(labeled):
                if sl is not None:
                    # ndimage returns (slice for axis 0 [rows=y], slice for axis 1 [cols=x])
                    y_slice, x_slice = sl
                    x_min, x_max = x_slice.start, x_slice.stop - 1
                    y_min, y_max = y_slice.start, y_slice.stop - 1
                    rect = Rectangle(
                        (x_min * step, y_min * step),
                        (x_max - x_min + 1) * step,
                        (y_max - y_min + 1) * step,
                        linewidth=2, edgecolor='red', facecolor='none', alpha=1.0
                    )
                    ax.add_patch(rect)

        if ax is None:
            fig, ax = plt.subplots()

        if keyword == "deposition":
            # Use half-step padded extent so pixel centers align to coordinates (0..size)
            dx = float(self.grid_step_mm)
            extent = (-dx / 2.0, self.size_mm + dx / 2.0, -dx / 2.0, self.size_mm + dx / 2.0)
            im = ax.imshow(self.deposition_mesh, extent=extent, origin='lower')
            plt.colorbar(im, ax=ax, label='Intensity')
            ax.set_title('Bed Mesh Deposition')
            ax.set_xlabel('X (mm)')
            ax.set_ylabel('Y (mm)')
            ax.grid(True, linestyle='--', alpha=0.3)
            # Ensure bool_mesh is a boolean numpy array
            bool_mesh = np.asarray(self.bool_mesh, dtype=bool)
            result = ndimage_label(bool_mesh)
            if isinstance(result, tuple):
                labeled, _ = result
            else:
                labeled = result
            step = self.grid_step_mm
            _plot_bounding_boxes(ax, labeled, step)
        elif keyword == "boxes":
            # Optionally show mask raster with correct extent to align with grid
            dx = float(self.grid_step_mm)
            extent = (-dx / 2.0, self.size_mm + dx / 2.0, -dx / 2.0, self.size_mm + dx / 2.0)
            if self._bool_masks:
                for mask in self._bool_masks:
                    ax.imshow(mask.mask, extent=extent, origin='lower', alpha=0.25, cmap='Greys')
            # Draw rectangles corresponding to connected True regions in bool_mesh
            bool_mesh = np.asarray(self.bool_mesh, dtype=bool)
            result = ndimage_label(bool_mesh)
            if isinstance(result, tuple):
                labeled, _ = result
            else:
                labeled = result
            ax.set_title('Boolean Mask Bounding Boxes')
            ax.set_xlabel('X (mm)')
            ax.set_ylabel('Y (mm)')
            ax.grid(True, linestyle='--', alpha=0.3)
            step = self.grid_step_mm
            _plot_bounding_boxes(ax, labeled, step)
            ax.set_xlim(0, self.size_mm)
            ax.set_ylim(0, self.size_mm)
        else:
            raise ValueError("Unknown keyword for plotting")

    def plot_bool_mask(self) -> None:
        """
        Plot the boolean mask.

        This method visualizes the boolean mask as a grayscale image.
        """
        import matplotlib.pyplot as plt
        plt.imshow(self.bool_mesh, cmap='gray', origin='lower', extent=(0, self.size_mm, 0, self.size_mm))
        plt.title("Boolean Mask")
        plt.colorbar()
        plt.show()

    def clear_deposition_mesh(self) -> None:
        """
        Clear the deposition mesh.

        This method resets the deposition mesh to zero.
        """
        self.deposition_mesh.fill(0)
