from meshing import BedMesh
from .SquaredSerpentine import SquaredSerpentine
from simulation import Scheduler
import numpy as np
import json
from datetime import datetime
from typing import List


class Optimizer:
    def __init__(self, bedmesh: BedMesh, squared_serpentines: List[SquaredSerpentine], verbose: bool = True):
        self.bedmesh = bedmesh
        self.squared_serpentines = squared_serpentines
        self.dev_vs_stride = []  # List to store standard deviation vs stride values
        self.verbose = verbose
        self.bool_masks = [s.mask for s in squared_serpentines]

    def _sim_routine(self, speed: float = 5):
        # 1. Grab points from all serpentines
        # 2. Create a scheduler with the bed and movements
        movements = []
        for serp in self.squared_serpentines:
            movements.extend(serp.serpentines)
        sim = Scheduler(bed=self.bedmesh, mov_list=movements)
        # 3. Start the simulation
        sim.start(live_plot=self.verbose, refresh_every=1)

    def span_std_vs_stride(
        self,
        strides: np.ndarray | list[float] | None = None,
        speed: float = 5.0,
        reset_mesh_each: bool = True,
        restore_stride: bool = False,
        plot: bool = True,
        ax=None,
        save_to_json: bool = False,
        return_figs: bool = False
    ):
        """
        Sweep the serpentine stride, simulate, and collect deposition std-dev for each stride.

        Args:
            strides: Iterable of stride values (in mm). If None, use a default decreasing sweep
                     from current stride to max(grid_step, current/5) with ~10 samples.
            speed: Movement speed passed to the scheduler.
            reset_mesh_each: If True, clears deposition mesh before each stride simulation.
            restore_stride: If True, restore the original stride at the end.
            plot: If True, plot dev_std vs stride.
            ax: Optional matplotlib axis to draw on (created if None and plot=True).

        Returns:
            (strides_array, dev_std_array, best_strides_array)
            best_strides_array: np.ndarray of best stride for each mask (or float if only one mask)
        """
        import matplotlib.pyplot as plt

        # Build stride sweep
        current = float(self.squared_serpentines[0].stride)
        if strides is None:
            # Default: decrease from current to a safe lower bound
            lower = max(float(self.bedmesh.grid_step_mm), current / 5.0, 0.05)
            strides = np.linspace(current, lower, num=10, retstep=False)
        strides_arr = np.asarray(list(strides), dtype=float)

        # Run sweep
        original_strides = [float(serp.stride) for serp in self.squared_serpentines]
        devs: List[List[float]] = []
        serpentines_amnt = len(self.squared_serpentines)
        for s in strides_arr:
            for serp in self.squared_serpentines:
                serp.set_stride(float(s))
            if reset_mesh_each:
                self.bedmesh.clear_deposition_mesh()
            self._sim_routine(speed=speed)
            dev_std = self.bedmesh.get_std_deviation(overall_dev=False)
            devs.append(dev_std)

        devs_arr = np.asarray(devs, dtype=float)

        # Store results
        self.dev_vs_stride = list(zip(map(float, strides_arr), devs))

        # Restore strides if requested
        if restore_stride:
            for serp, orig in zip(self.squared_serpentines, original_strides):
                serp.set_stride(orig)

        best_strides = None  # Will be set below
        best_devs = None
        best_stride = None
        best_dev = None
        figs = []
        # Plot if requested
        if plot:
            import matplotlib
            matplotlib.use('Agg')  # Ensure non-interactive backend
            import matplotlib.pyplot as plt
            devs_arr = np.asarray(devs, dtype=float)
            # Check if we have multiple masks (devs_arr shape: (n_strides, n_masks))
            if devs_arr.ndim == 2 and devs_arr.shape[1] > 1:
                n_masks = devs_arr.shape[1]
                fig, axs = plt.subplots(n_masks, 1)
                figs.append(fig)
                # Ensure axs is always a list for consistent indexing
                if n_masks == 1:
                    axs_list = [axs]
                elif not isinstance(axs, (list, np.ndarray)):
                    axs_list = [axs]
                else:
                    axs_list = axs
                for i in range(n_masks):
                    ax_i = axs_list[i]
                    ax_i.plot(strides_arr, devs_arr[:, i], marker="o", linestyle="-", label=f"Mask {i+1}")
                    ax_i.set_ylabel("Deposition Std Dev")
                    ax_i.set_title(f"Mask {i+1}: Deposition Std Dev vs Stride")
                    ax_i.grid(True, linestyle='--', alpha=0.3)
                    ax_i.legend()
                # Set xlabel on the last subplot
                axs_list[-1].set_xlabel("Stride (mm)")
                plt.tight_layout()
                if not return_figs:
                    plt.show()
                # Find best stride for each mask
                best_stride_idxs = np.argmin(devs_arr, axis=0)
                best_strides = strides_arr[best_stride_idxs]
                best_devs = devs_arr[best_stride_idxs, range(n_masks)]
                # Simulate and plot for the best stride of the first mask (as example)
                best_stride = float(best_strides[0])
                best_dev = float(best_devs[0])
            else:
                # Single mask or overall
                fig, ax = plt.subplots()
                figs.append(fig)
                ax.plot(strides_arr, devs_arr.flatten(), marker="o", linestyle="-", label="std vs stride")
                ax.set_xlabel("Stride (mm)")
                ax.set_ylabel("Deposition Std Dev")
                ax.set_title("Deposition Std Dev vs Stride")
                ax.grid(True, linestyle='--', alpha=0.3)
                ax.legend()
                if not return_figs:
                    plt.show()
                best_stride_idx = int(np.argmin(devs_arr))
                best_stride = float(strides_arr[best_stride_idx])
                best_dev = float(devs_arr.flatten()[best_stride_idx])
                best_strides = best_stride
                best_devs = best_dev

            # Simulate deposition for the best stride(s) on a fresh mesh
            for serp in self.squared_serpentines:
                serp.set_stride(best_stride)
            self.bedmesh.clear_deposition_mesh()
            self._sim_routine(speed=speed)

            fig2, ax2 = plt.subplots()
            figs.append(fig2)
            self.bedmesh.plot(keyword="deposition", ax=ax2)
            self.bedmesh.plot(keyword="boxes", ax=ax2)
            for serp in self.squared_serpentines:
                serp.draw(ax=ax2)
            # Set summary title with all best strides and std devs if multiple masks
            if isinstance(best_strides, np.ndarray) and best_strides.size > 1:
                strides_str = ", ".join(f"{s:.3f}" for s in best_strides)
                if isinstance(best_devs, (list, np.ndarray)):
                    devs_str = ", ".join(f"{d:.4f}" for d in best_devs)
                else:
                    devs_str = f"{best_devs:.4f}"
                ax2.set_title(f"Best strides: [{strides_str}] mm\nDep Stds: [{devs_str}]")
            else:
                ax2.set_title(f"Best stride: {best_stride:.3f} mm — Dep Std: {best_dev:.4f}")
            ax2.set_xlabel("X (mm)")
            ax2.set_ylabel("Y (mm)")
            ax2.grid(True, linestyle='--', alpha=0.3)
            if not return_figs:
                plt.show()

            # Restore original strides if requested
            if restore_stride:
                for serp, orig in zip(self.squared_serpentines, original_strides):
                    serp.set_stride(orig)
            if save_to_json:
                timestamp = datetime.now().isoformat()
                bool_mask_info = []
                for mask in self.bool_masks:
                    bool_mask_info.append({
                        "size": mask.size_mm,
                        "position": mask.specific_args["corner1"],
                        "shape": (mask.specific_args["x_size"], mask.specific_args["y_size"])
                    })
                with open(f"logs/dev_vs_stride_{timestamp.replace(':', '-')}.json", "w") as f:
                    json.dump({
                        "dev_vs_stride": [(float(s), [float(d) for d in dev]) for s, dev in self.dev_vs_stride],
                        "best_strides": best_strides.tolist() if isinstance(best_strides, np.ndarray) else float(best_strides),
                        "best_devs": best_devs.tolist() if isinstance(best_devs, np.ndarray) else float(best_devs),
                        "bool_masks": [
                            {
                                "size": float(mask.size_mm),
                                "position": [float(coord) for coord in mask.specific_args["corner1"]],
                                "shape": [int(mask.specific_args["x_size"]), int(mask.specific_args["y_size"])]
                            }
                            for mask in self.bool_masks
                        ]
                    }, f, indent=4)
        if return_figs:
            return strides_arr, devs_arr, best_strides, figs
        return strides_arr, devs_arr, best_strides

    def plot_status(self):
        """Plot the current status of the bed mesh and serpentines, overlapping all elements."""
        import matplotlib
        matplotlib.use('Agg')  # Ensure non-interactive backend
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots()

        # Plot bedmesh deposition as a colored mesh
        self.bedmesh.plot(keyword="deposition", ax=ax)

        self.bedmesh.plot(keyword="boxes", ax=ax)
        # Draw all squared serpentines
        for serp in self.squared_serpentines:
            serp.draw(ax=ax)

        print(
            f"Current strides: {[serp.stride for serp in self.squared_serpentines]}, margins: {[serp.margin for serp in self.squared_serpentines]}")
        plt.show()
