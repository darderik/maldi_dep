import numpy as np
from numpy import ndarray as NDArray
from typing import Optional, Callable, Tuple
from scipy.ndimage import shift
from functools import singledispatch
from .utils import boolean_function
from .BedMesh import BedMesh

class Nozzle:
    def __init__(self, nozzle_function: Optional[Callable], owner_bed: "BedMesh"):
        from wrapper.Config import Config

        # Create a mesh equal to the bed but will apply gaussian
        size_mm = owner_bed.size_mm
        self.size_mm = size_mm
        self.step = owner_bed.grid_step_mm
        # This is an estimate, linspace will pad
        steps_count: int = owner_bed.steps_count
        self.steps_count = steps_count
        self._bed = owner_bed
        # mesh_size is assumed square
        # Spray mask
        from .Mask import SprayMask
        self.spray_mask = None
        if nozzle_function is not None:
            # Compute kernel diameter from current Z via Config
            z = Config().get_height()
            diameter_mm = Config()._get_diameter_for_z(z)
            if diameter_mm <= 0:
                # Fallback to small default if configuration returns invalid value
                diameter_mm = max(self.step * 3.0, 1.0)
            radius_mm = diameter_mm / 2.0
            # Build a small, centered kernel in [-radius, +radius]
            self.spray_mask = SprayMask(
                size_mm=diameter_mm,
                grid_step_mm=self.step,
                function=nozzle_function,
                bottom_limit=-radius_mm,
                upper_limit=+radius_mm,
            )
            # Diagnostics: expose kernel size and kernel mesh
            self.spray_diameter_mm = diameter_mm
            self.spray_mask_mesh = self.spray_mask.mask

    def spray(self, apply_position: Tuple[float, float] | NDArray = (0, 0), time: float = 0) -> None:
        """Apply the spray mask to the bed mesh."""
        if self.spray_mask is None:
            raise ValueError("No spray function configured for this nozzle")
        # Kernel is centered at 0,0 in its local coordinates
        mask_anchor = (0.0, 0.0)
        self.spray_mask.apply(
            self._bed,
            apply_position=apply_position,
            mask_anchor=mask_anchor,
            time=time
        )

    def plot(self) -> None:
        """Plot the nozzle mesh."""
        if self.spray_mask is None:
            raise ValueError("No spray function configured for this nozzle")
        import matplotlib.pyplot as plt
        plt.imshow(self.spray_mask.mask, extent=(-self.spray_diameter_mm/2, self.spray_diameter_mm/2,
                   -self.spray_diameter_mm/2, self.spray_diameter_mm/2), origin='lower')
        plt.colorbar(label='Intensity')
        plt.title('Nozzle Mesh')
        plt.xlabel('X (mm)')
        plt.ylabel('Y (mm)')
        plt.show()
