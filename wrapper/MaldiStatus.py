from typing import Any, List, Optional, Tuple
from .Config import Config, SampleConfig
from numpy import ndarray as NDArray
from meshing import BedMesh, SampleMask
import numpy as np
from optimizer import SquaredSerpentine, Optimizer
from gcode import MaskMovement, GCodeCreator
import os
import json
from dataclasses import dataclass
from scipy.interpolate import interp1d

@dataclass
class SampleAggregator:
    sample_mask: SampleMask
    serpentine: SquaredSerpentine
    bl_corner: Tuple[float, float]
    x_size: float
    y_size: float
    optimizer: Optional[Optimizer] = None


class MaldiStatus:
    _instance: Optional["MaldiStatus"] = None

    def __init__(self):
        self.config: Config = Config()
        self.bed_mesh: Optional[BedMesh] = None
        self.samples: List[SampleAggregator] = []
        self.initialized = True
        self.gcode_creator: Optional[GCodeCreator] = None
    def refresh_bed_mesh(self) -> None:
        self.bed_mesh = BedMesh(
            size_mm=Config().get("bed_size_mm"),
            grid_step_mm=Config().get("grid_step"),
            spray_function=self.gaussian_function
        )
        self.samples = []  # Clear existing samples when refreshing bed mesh

    def add_sample(self, sample_config: SampleConfig ,verbose: bool = False) -> None:
        if self.bed_mesh is None:
            self.refresh_bed_mesh()
        assert self.bed_mesh is not None
        sample_defaults = self.config._sample_defaults
        x_size = sample_config.get("x_size") or sample_defaults.get("x_size", 10)
        y_size = sample_config.get("y_size") or sample_defaults.get("y_size", 10)
        bl_corner = sample_config.get("bl_corner") or (0, 0)

        # Object creation
        samplemask: Optional[SampleMask] = self.bed_mesh.add_bool_mask(
            points=[[bl_corner[0], bl_corner[0]+x_size, bl_corner[1], bl_corner[1]+y_size]],
            shape="rectangle"
        )
        assert samplemask is not None
        serp = SquaredSerpentine(
                bm=self.bed_mesh,
                bool_mask=samplemask,
                margin=sample_config.get("margin"),
                x_amnt=Config().get("x_points"),
                stride=Config().get("stride"),
                speed=Config().get("speed"),
                max_speed=Config().get("max_speed"),
                passes=sample_config.get("passes"),
                alternate_offset=sample_config.get("alternate_offset"),
                )
        assert serp is not None
        opti = Optimizer(bed_mesh=self.bed_mesh, serpentine=serp, verbose=verbose)
        ## Sample aggregator
        s_aggregator = SampleAggregator(
            sample_mask=samplemask,
            serpentine=serp,
            bl_corner=bl_corner,
            x_size=x_size,
            y_size=y_size,
            optimizer=opti
        )
        self.samples.append(s_aggregator)

    def get_samples(self) -> List[SampleMask]:
        if self.bed_mesh is None:
            self.refresh_bed_mesh()
        assert self.bed_mesh is not None
        return self.bed_mesh._bool_masks

    def get_samples_info(self) -> List[dict]:
        if self.bed_mesh is None:
            self.refresh_bed_mesh()
        assert self.bed_mesh is not None
        samples_objs: List[SampleMask] = self.bed_mesh._bool_masks
        # Parse into reduced list
        samples_info = []
        for mask in samples_objs:
            blc = mask.bl_corner
            xs = mask.x_size
            ys = mask.y_size
            samples_info.append({"bl_corner": blc, "x_size": xs, "y_size": ys})
        return samples_info

    def get_sample_aggregator(self, index: int) -> Optional[SampleAggregator]:
        if 0 <= index < len(self.samples):
            return self.samples[index]
        return None


    def gaussian_function(self,mesh: Tuple[NDArray, NDArray]) -> NDArray:
        z_height = Config().get("z_height")
        if z_height is not None:
            diameter = Config()._get_diameter_for_z(z_height)
        else:
            raise ValueError("z_height must not be None")
        # Compute sigma from diameter
        if diameter is None or diameter <= 0:
            raise ValueError("Invalid diameter computed from z_height.")
        sigma = diameter/4.5
        x, y = mesh
        return 50*np.exp(-(x**2 + y**2) / (2 * sigma**2)) / (2 * np.pi * sigma**2)

    def _apply_stride_for_all(self, stride: float) -> None:
        """Helper to apply the stride to all sample serpentines."""
        for s_agg in self.samples:
            s_agg.serpentine.set_stride(stride)

    def optimize_strides(self,
                        save_to_json: bool = True,
                        plot: bool = True,
                        return_figs: bool = False,
                        progress_callback = None):
        """
        Optimize serpentine strides and return best stride for the selected sample.
        
        Args:
            save_to_json: Whether to save results to JSON file
            plot: Whether to plot results
            return_figs: Whether to return matplotlib figures
            progress_callback: Optional callback function that receives (current_step, total_steps)
        """
        if not self.samples:
            raise ValueError("No samples available. Add a sample first.")

        best_strides: List[float] = []
        for idx, s_aggregator in enumerate(self.samples):
            if s_aggregator.optimizer is None:
                continue
            # Prepare parameters from Config
            minimum_stride = Config().get("minimum_stride")
            maximum_stride = Config().get("maximum_stride")
            stride_steps = Config().get("stride_steps")
            strides = np.linspace(minimum_stride, maximum_stride, stride_steps)
            # Use the provided flag directly
            save_json = save_to_json

            s_aggregator.optimizer.span_std_vs_stride(
                strides=strides,
                save_to_json=save_json,
                plot=plot,
                return_figs=return_figs,
                progress_callback=progress_callback
            )
            series = [float(np.mean(devs)) if isinstance(devs, (list, np.ndarray)) else float(devs)
                      for _, devs in s_aggregator.optimizer.dev_vs_stride]
            best_idx = int(np.argmin(series))
            best_stride = float(s_aggregator.optimizer.dev_vs_stride[best_idx][0])
            best_strides.append(best_stride)
        # Fallback if sample_idx out of range
        return best_strides
    def gcode_from_specific_stride(self, stride:float, output_file: str = "output_specific_stride.gcode") -> str:
        """
        Generate G-code using a specific stride value for all samples.
        """
        if not self.samples:
            raise ValueError("No samples available. Add a sample first.")
        self._apply_stride_for_all(stride)
        return self.generate_gcode(output_file)

    def load_strides_from_json(self, json_file: Optional[str] = None) -> List[float]:
        """
        Load optimized stride values from a JSON file.
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
        Generate G-code from the current samples' serpentines.
        """
        if self.bed_mesh is None:
            self.refresh_bed_mesh()
        if not self.samples:
            raise ValueError("No samples available. Add a sample first.")

        gcode_packed: List[SampleAggregator] = []
        for s_agg in self.samples:
            gcode_packed.append(s_agg)
        # Temps from Config
        z_height = Config().get("z_height")
        bed_temp = Config().get("bed_temperature")
        nozzle_temp = Config().get("nozzle_temperature")

        self.gcode_creator = GCodeCreator(
            data=gcode_packed,
            z_height=z_height,
            bed_temp=bed_temp,
            nozzle_temp=nozzle_temp
        )
        resulting_gcode = self.gcode_creator.generate_gcode()
        
        # Save to file
        with open(output_file, "w") as f:
            f.write(resulting_gcode)
        
        return output_file

    def estimate_gcode_time(self) -> dict:
        """
        Estimate print time for a G-code file.
        
        Args:
            gcode_file: Path to the G-code file
            
        Returns:
            Dictionary with time estimates
        """
        if self.gcode_creator is None:
            raise ValueError("GCodeCreator not initialized.")
        return self.gcode_creator.estimate_print_time()         

    def simulate_manual_stride(self, stride: float, return_fig: bool = False, progress_callback = None) -> Optional[Any]:
        """
        Simulate deposition with a manual stride value (applied to all samples).
        
        Args:
            stride: Stride value to use for simulation
            return_fig: Whether to return matplotlib figure
            progress_callback: Optional callback function that receives (current_step, total_steps)
        """
        if self.bed_mesh is None:
            self.refresh_bed_mesh()
        if not self.samples:
            raise ValueError("No samples available. Add a sample first.")
        assert self.bed_mesh is not None

        # Apply the stride to all serpentines
        self._apply_stride_for_all(stride)
        
        # Clear deposition mesh
        self.bed_mesh.clear_deposition_mesh()
        
        # Create movements and simulate
        movements = []
        for s_agg in self.samples:
            movements.extend(s_agg.serpentine.movements)
        
        from simulation import Scheduler
        sim = Scheduler(bed=self.bed_mesh, mov_list=movements)
        sim.start(live_plot=False, refresh_every=1, progress_callback=progress_callback)  # No live plot for webapp
        
        # Plot if requested
        if return_fig:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots()
            self.bed_mesh.plot(keyword="deposition", ax=ax)
            self.bed_mesh.plot(keyword="boxes", ax=ax)
            for s_agg in self.samples:
                s_agg.serpentine.draw(ax=ax)
            ax.set_title(f"Deposition Map - Stride: {stride:.3f} mm")
            ax.set_xlabel("X (mm)")
            ax.set_ylabel("Y (mm)")
            ax.grid(True, linestyle='--', alpha=0.3)
            return fig
        
        return None

    def visualize_optimized_samples(self, best_strides: List[float]) -> Any:
        """
        Visualize all samples with their optimal strides applied, showing deposition patterns.
        
        Args:
            best_strides: List of optimal stride values for each sample
            
        Returns:
            matplotlib figure showing the deposition map
        """
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        
        if self.bed_mesh is None:
            self.refresh_bed_mesh()
        assert self.bed_mesh is not None
        if not self.samples:
            raise ValueError("No samples available.")
        
        # Apply best strides to all samples
        for i, (s_agg, stride) in enumerate(zip(self.samples, best_strides)):
            s_agg.serpentine.set_stride(stride)
        
        # Clear deposition mesh and simulate
        self.bed_mesh.clear_deposition_mesh()
        movements = []
        for s_agg in self.samples:
            movements.extend(list(s_agg.serpentine.movements))
        
        from simulation import Scheduler
        sim = Scheduler(bed=self.bed_mesh, mov_list=movements)
        sim.start(live_plot=False, refresh_every=1)
        
        # Create visualization
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Plot deposition mesh
        self.bed_mesh.plot(keyword="deposition", ax=ax)
        
        # Plot sample boxes with best stride annotations
        self.bed_mesh.plot(keyword="boxes", ax=ax)
        
        # Draw serpentines and annotate with stride values
        for i, (s_agg, stride) in enumerate(zip(self.samples, best_strides)):
            s_agg.serpentine.draw(ax=ax)
            # Add text annotation with stride value
            center_x = s_agg.bl_corner[0] + s_agg.x_size / 2
            center_y = s_agg.bl_corner[1] + s_agg.y_size / 2
        ax.set_title("Optimized Deposition Map - All Samples", fontsize=14, weight='bold')
        ax.set_xlabel("X (mm)", fontsize=12)
        ax.set_ylabel("Y (mm)", fontsize=12)
        ax.grid(True, linestyle='--', alpha=0.3)
        
        return fig

