from typing import Any, List, Optional, Tuple
from scipy.stats import linregress
from .Config import Config
from numpy import ndarray as NDArray
from typing import Tuple
from meshing import BedMesh
import numpy as np
from optimizer import SquaredSerpentine, Optimizer
from gcode import MaskMovement, GCodeCreator
import os
import json
from datetime import datetime

class Wrapper:
    def __init__(self, bed_size: Optional[float] = None, z_height: Optional[float] = None, speed: Optional[float] = None, spray_function: Optional[str] = None, spray_radius_vs_z: Optional[List[List[float]]] = None, grid_step: Optional[float] = None, nozzle_temp: Optional[float] = None, bed_temp: Optional[float] = None):
        if bed_size is None:
            bed_size = Config().get("bed_size")
        if z_height is None:
            z_height = Config().get("z_height")
        if speed is None:
            speed = Config().get("speed")
        if spray_function is None:
            spray_function = Config().get("spray_function")
        if spray_radius_vs_z is None:
            spray_radius_vs_z = Config().get("spray_radius_vs_z")
        if grid_step is None:
            grid_step = Config().get("grid_step", 1.5)
        if nozzle_temp is None:
            nozzle_temp = Config().get("nozzle_temperature", 100.0)
        if bed_temp is None:
            bed_temp = Config().get("bed_temperature", 40.0)
        

        # None checks
        if not all([isinstance(var, (int, float)) for var in [bed_size, z_height, speed]]):
            raise ValueError("bed_size, z_height, and speed must be numeric values.")
        self.bed_size = bed_size
        self.z_height = z_height
        self.speed = speed
        self.grid_step = grid_step
        self.spray_radius_vs_z = linregress(x=spray_radius_vs_z[0], y=spray_radius_vs_z[1]) if spray_function else None
        self.spray_function = spray_function
        self.nozzle_temp = nozzle_temp
        self.bed_temp = bed_temp
        
        # Create the bed mesh instance
        self.bed_mesh_instance = BedMesh(size_mm=self.bed_size, grid_step_mm=self.grid_step, spray_function=self.gaussian_function)
        
        self.samples: List[Any] = []
        # Storage for serpentines and optimizers
        self.serpentines: List[SquaredSerpentine] = []
        self.optimizers: List[Optimizer] = []
        
        self._load_samples()
    
    def _load_samples(self) -> None:
        samples: List[Any] = Config().get("samples", []) or []
        for sample in samples:
            shape = sample.get("type")
            position = sample.get("position", [0, 0])
            size = sample.get("size", [10, 10])
            if shape == "rectangle":
                x_min, y_min = position
                x_size, y_size = size
                x_max, y_max = x_min + x_size, y_min + y_size
                self.bed_mesh_instance.add_bool_mask(points=[[x_min, x_max, y_min, y_max]], shape="rectangle")
                self.samples.append(sample)
            else:
                raise ValueError(f"Unsupported shape type: {shape}")
        
        
    def _get_radius_for_z(self, z: float) -> Optional[float]:
        if self.spray_radius_vs_z:
            slope, intercept = self.spray_radius_vs_z.slope, self.spray_radius_vs_z.intercept
            return slope * z + intercept
        return None


    def gaussian_function(self,mesh: Tuple[NDArray, NDArray]) -> NDArray:
        if self.z_height is not None:
            radius = self._get_radius_for_z(self.z_height)
        else:
            raise ValueError("z_height must not be None")
        # Compute sigma from radius
        if radius is None or radius <= 0:
            raise ValueError("Invalid radius computed from z_height.")
        sigma = radius / 2
        x, y = mesh
        return 100*np.exp(-(x**2 + y**2) / (2 * sigma**2)) / (2 * np.pi * sigma**2)

    def _get_stride_range(self, idx: int) -> List[float]:
        sample_mask_data = self.samples[idx] if idx < len(self.samples) else {}
        stride_data = sample_mask_data.get("strides", [])
        stride_data = stride_data[0] if isinstance(stride_data, tuple) else stride_data
        strides = np.linspace(stride_data[0], stride_data[1], stride_data[2])
        return strides

    def create_serpentine(self):
        pass
    def create_serpentines(self) -> None:
        """
        Create serpentine patterns for all masks in the bed mesh.
        Uses the wrapper's configured speed.
        """
        self.serpentines = []
        for idx in range(len(self.bed_mesh_instance._bool_masks)):
            boolmask = self.bed_mesh_instance._bool_masks[idx]
            sample_mask_data = self.samples[idx] if idx < len(self.samples) else {}
            serp = SquaredSerpentine(
                bm=self.bed_mesh_instance,
                bool_mask=boolmask,
                margin=sample_mask_data.get("margin", 10),
                x_amnt=sample_mask_data.get("x_amount", 10),
                stride=1.0,  # Initial stride, will be optimized later
                passes=sample_mask_data.get("passes", 2),
                speed=float(self.speed) if self.speed is not None else 40.0
            )
            self.serpentines.append(serp)
            self.optimizers.append(
                Optimizer(bedmesh=self.bed_mesh_instance, squared_serpentines=[serp], verbose=False)
            )

    def optimize_strides(self,
                        sample_idx: int = 0,
                        save_to_json: bool = True,
                        plot: bool = True,
                        return_figs: bool = False) -> Tuple[Optional[List[float]], Optional[List[Any]]]:
        """
        Optimize serpentine strides using the configured optimizers.
        
        Args:
            strides_to_test: Array of strides to test during optimization
            save_to_json: Whether to save results to JSON
            plot: Whether to plot optimization results
            return_figs: Whether to return matplotlib figures
            
        Returns:
            List of best strides, or None if no optimization performed
        """
        self.create_serpentines()
        sample_data = self.samples[sample_idx] if sample_idx < len(self.samples) else {}
        strides_to_test = self._get_stride_range(sample_idx)
        
        best_strides_list = []
        figs_list = []
        for opt in self.optimizers:
            result = opt.span_std_vs_stride(
                strides=strides_to_test,
                speed=float(self.speed) if self.speed is not None else 40.0,
                save_to_json=save_to_json,
                plot=plot,
                return_figs=return_figs
            )
            if return_figs and len(result) == 4:
                strides_arr, devs_arr, best_stride, figs = result
                figs_list.extend(figs)
            else:
                strides_arr, devs_arr, best_stride = result
            if best_stride is not None:
                if isinstance(best_stride, (list, np.ndarray)):
                    best_strides_list.extend(best_stride)
                else:
                    best_strides_list.append(best_stride)
        
        # Apply the best strides to serpentines
        if best_strides_list:
            self.apply_strides(best_strides_list)
            if return_figs:
                return best_strides_list, figs_list
            return best_strides_list, None
        if return_figs:
            return None, []
        return None, None
    
    def apply_strides(self, strides: List[float]) -> None:
        """
        Apply stride values to serpentines.
        
        Args:
            strides: List of stride values (can be a single value or one per serpentine)
        """
        if isinstance(strides, (float, int)):
            for serp in self.serpentines:
                serp.set_stride(strides)
        else:
            for i, serp in enumerate(self.serpentines):
                if i < len(strides):
                    serp.set_stride(strides[i])
    def gcode_from_specific_stride(self, stride:float, output_file: str = "output_specific_stride.gcode") -> str:
        """
        Generate G-code using a specific stride value for all serpentines.
        
        Args:
            stride: Stride value to apply
            output_file: Output filename
        Returns:
            Path to the generated G-code file
        """
        self.apply_strides([stride])
        return self.generate_gcode(output_file)

    def load_strides_from_json(self, json_file: Optional[str] = None) -> List[float]:
        """
        Load optimized stride values from a JSON file.
        
        Args:
            json_file: Path to the JSON file. If None, uses the most recent dev_vs_stride file.
            
        Returns:
            List of stride values
        """
        # Find the most recent dev_vs_stride JSON file if not specified
        if json_file is None:
            json_files = [f for f in os.listdir('logs') if f.startswith('dev_vs_stride_') and f.endswith('.json')]
            if not json_files:
                raise FileNotFoundError("No dev_vs_stride JSON files found.")
            # Sort by timestamp
            json_files.sort(reverse=True)
            json_file = os.path.join('logs', json_files[0])
        
        # Load the JSON
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        best_strides = data.get('best_strides')
        if best_strides is None:
            raise ValueError("No best_strides found in JSON.")
        
        return best_strides if isinstance(best_strides, list) else [best_strides]

    def generate_gcode(self, output_file: str = "output.gcode") -> str:
        """
        Generate G-code from the current serpentines.
        
        Args:
            output_file: Output filename
            
        Returns:
            Path to the generated G-code file
        """
        if not self.serpentines:
            self.create_serpentines()
        
        gcode_packed: List[MaskMovement] = []
        for serp in self.serpentines:
            gcode_packed.append(MaskMovement(serp.mask, serp.serpentines))
        z_height = Config().get("z_height", 10.0)
        gcode_creator = GCodeCreator(data=gcode_packed, bed_temp=self.bed_temp, nozzle_temp=self.nozzle_temp, z_height=z_height)
        resulting_gcode = gcode_creator.generate_gcode()
        
        # Save to file
        with open(output_file, "w") as f:
            f.write(resulting_gcode)
        
        return output_file

    def simulate_manual_stride(self, stride: float, return_fig: bool = False) -> Optional[Any]:
        """
        Simulate deposition with a manual stride value and optionally return the plot figure.
        
        Args:
            stride: The stride value to apply to all serpentines
            return_fig: Whether to return the matplotlib figure
            
        Returns:
            The matplotlib figure if return_fig=True, None otherwise
        """
        if not self.serpentines:
            self.create_serpentines()
        
        # Apply the stride to all serpentines
        self.apply_strides([stride] * len(self.serpentines))
        
        # Clear deposition mesh
        self.bed_mesh_instance.clear_deposition_mesh()
        
        # Create movements and simulate
        movements = []
        for serp in self.serpentines:
            movements.extend(serp.serpentines)
        
        from simulation import Scheduler
        sim = Scheduler(bed=self.bed_mesh_instance, mov_list=movements)
        sim.start(live_plot=False, refresh_every=1)  # No live plot for webapp
        
        # Plot if requested
        if return_fig:
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots()
            self.bed_mesh_instance.plot(keyword="deposition", ax=ax)
            self.bed_mesh_instance.plot(keyword="boxes", ax=ax)
            for serp in self.serpentines:
                serp.draw(ax=ax)
            ax.set_title(f"Deposition Map - Stride: {stride:.3f} mm")
            ax.set_xlabel("X (mm)")
            ax.set_ylabel("Y (mm)")
            ax.grid(True, linestyle='--', alpha=0.3)
            return fig
        
        return None

