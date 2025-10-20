import numpy as np
from numpy import ndarray as NDArray
from typing import Optional, Callable, Tuple
from scipy.ndimage import shift
from functools import singledispatch
from .utils import boolean_function
from .BedMesh import BedMesh


class Nozzle:
    def __init__(self, nozzle_function: Optional[Callable], owner_bed: "BedMesh"):
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
            self.spray_mask = SprayMask(
                size_mm=size_mm,
                grid_step_mm=self.step,
                function=nozzle_function,
                # Center gaussian on the nozzle n
                bottom_limit=-size_mm / 2,
                upper_limit=size_mm / 2,
            )

    def spray(self, apply_position: Tuple[float, float] | NDArray = (0, 0), time: float = 0) -> None:
        """Apply the spray mask to the bed mesh."""
        if self.spray_mask is None:
            raise ValueError("No spray function configured for this nozzle")
        mask_anchor = (self.size_mm / 2, self.size_mm / 2)
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
        plt.imshow(self.spray_mask.mask, extent=(-self._bed.size_mm / 2, self._bed.size_mm /
                   2, -self._bed.size_mm / 2, self._bed.size_mm / 2), origin='lower')
        plt.colorbar(label='Intensity')
        plt.title('Nozzle Mesh')
        plt.xlabel('X (mm)')
        plt.ylabel('Y (mm)')
        plt.show()
