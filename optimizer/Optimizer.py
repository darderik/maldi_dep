from meshing import BedMesh
from .SquaredSerpentine import SquaredSerpentine
from simulation import Scheduler
import numpy as np
import json
from datetime import datetime
from typing import List, Optional, Callable


class Optimizer:
    def __init__(self, bed_mesh: BedMesh, serpentine: SquaredSerpentine, verbose: bool = True):
        self.bed_mesh = bed_mesh
        self.serpentine = serpentine
        self.dev_vs_stride = []  # List to store standard deviation vs stride values
        self.verbose = verbose
        # Keep a single-mask list for downstream JSON compatibility
        self.bool_masks = [self.serpentine.mask]

    def _sim_routine(self, speed: float = 5, progress_callback: Optional[Callable[[int, int], None]] = None):
        # Build scheduler from the single serpentine movements
        movements = list(self.serpentine.movements)
        sim = Scheduler(bed=self.bed_mesh, mov_list=movements)
        sim.start(live_plot=self.verbose, refresh_every=1, progress_callback=progress_callback)

    def span_std_vs_stride(
        self,
        strides: np.ndarray | list[float] | None = None,
        reset_mesh_each: bool = True,
        restore_stride: bool = False,
        plot: bool = True,
        ax=None,
        save_to_json: bool = False,
        return_figs: bool = False,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ):
        """
        Sweep the serpentine stride, simulate, and collect deposition std-dev for each stride.

        Args:
            progress_callback: Optional callback function that receives (current_step, total_steps)
                             for progress updates.

        Returns:
            (strides_array, dev_std_array, best_stride[, figs])
        """
        import matplotlib.pyplot as plt
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import os

        # Build stride sweep starting from current stride of the single serpentine
        speed = self.serpentine.speed
        current = float(self.serpentine.stride)
        if strides is None:
            lower = max(float(self.bed_mesh.grid_step_mm), current / 5.0, 0.05)
            strides = np.linspace(current, lower, num=10, retstep=False)
        strides_arr = np.asarray(list(strides), dtype=float)

        # Prepare immutable mask info to reproduce masks in worker beds
        mask0 = self.bool_masks[0]
        blc = getattr(mask0, 'bl_corner', (0.0, 0.0))
        xs = float(getattr(mask0, 'x_size', 0.0))
        ys = float(getattr(mask0, 'y_size', 0.0))

        # Worker: run a full sim for a given stride on an isolated BedMesh
        def _eval_stride(index: int, s_val: float):
            bm = BedMesh(
                size_mm=self.bed_mesh.size_mm,
                grid_step_mm=self.bed_mesh.grid_step_mm,
                spray_function=self.bed_mesh.spray_function,
            )
            # Recreate the boolean mask on this bed
            bm.add_bool_mask(points=[float(blc[0]), float(blc[0]) + xs, float(blc[1]), float(blc[1]) + ys], shape="rectangle")
            serp = SquaredSerpentine(
                bm=bm,
                bool_mask=bm._bool_masks[0],
                margin=self.serpentine.margin,
                x_amnt=self.serpentine.x_amnt,
                stride=float(s_val),
                speed=self.serpentine.speed,
                max_speed=self.serpentine.max_speed,
                passes=self.serpentine.passes,
                alternate_offset=self.serpentine.alternate_offset,
            )
            sim = Scheduler(bed=bm, mov_list=list(serp.movements))
            sim.start(live_plot=False)
            dev_std = bm.get_std_deviation(overall_dev=False)
            return index, float(s_val), dev_std

        # Launch all in a thread pool
        total_strides = len(strides_arr)
        max_workers = min(32, (os.cpu_count() or 1) * 2)
        futures = []
        results_by_index: dict[int, tuple[float, List[float]]] = {}
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            for idx, s in enumerate(strides_arr):
                futures.append(ex.submit(_eval_stride, idx, float(s)))
            completed = 0
            for fut in as_completed(futures):
                idx, s_val, dev_std = fut.result()
                results_by_index[idx] = (s_val, dev_std)
                completed += 1
                if progress_callback:
                    progress_callback(completed, total_strides)

        # Order results according to input strides
        ordered = [results_by_index[i] for i in range(total_strides)]
        strides_arr = np.asarray([s for (s, _) in ordered], dtype=float)
        devs = [dev for (_, dev) in ordered]
        devs_arr = np.asarray(devs, dtype=float)

        # Store results
        self.dev_vs_stride = list(zip(map(float, strides_arr), devs))

        # Determine best stride (use mean across components if multiple connected regions are found)
        if devs_arr.ndim == 2:
            series = devs_arr.mean(axis=1)
        else:
            series = devs_arr
        best_stride_idx = int(np.argmin(series))
        best_stride = float(strides_arr[best_stride_idx])
        best_dev = float(series[best_stride_idx])

        figs = []
        # Plot the best stride result if requested
        if plot:
            figs.append(None)
            # Simulate deposition for the best stride on the main bed for visualization
            original_stride = float(self.serpentine.stride)
            self.serpentine.set_stride(best_stride)
            self.bed_mesh.clear_deposition_mesh()
            self._sim_routine(speed=speed)

            self._ensure_interactive_backend()
            fig2, ax2 = plt.subplots()
            figs.append(fig2)
            self.bedmesh_plot(ax2)
            self.serpentine.draw(ax=ax2)
            ax2.set_title(f"Best stride: {best_stride:.3f} mm — Dep Std: {best_dev:.4f}")
            ax2.set_xlabel("X (mm)")
            ax2.set_ylabel("Y (mm)")
            ax2.grid(True, linestyle='--', alpha=0.3)
            if not return_figs:
                plt.show()
            if restore_stride:
                self.serpentine.set_stride(original_stride)

            if save_to_json:
                timestamp = datetime.now().isoformat()
                def _mask_info(mask):
                    pos = getattr(mask, 'bl_corner', None)
                    xs = getattr(mask, 'x_size', None)
                    ys = getattr(mask, 'y_size', None)
                    if pos is not None and xs is not None and ys is not None:
                        return {
                            "size": float(getattr(mask, 'size_mm', 0.0)),
                            "position": [float(pos[0]), float(pos[1])],
                            "shape": [int(xs), int(ys)]
                        }
                    if hasattr(mask, 'specific_args'):
                        sa = mask.specific_args
                        return {
                            "size": float(getattr(mask, 'size_mm', 0.0)),
                            "position": [float(c) for c in sa.get("corner1", (0.0, 0.0))],
                            "shape": [int(sa.get("x_size", 0)), int(sa.get("y_size", 0))]
                        }
                    return {"size": 0.0, "position": [0.0, 0.0], "shape": [0, 0]}
                with open(f"logs/dev_vs_stride_{timestamp.replace(':', '-')}.json", "w") as f:
                    json.dump({
                        "dev_vs_stride": [(float(s), [float(d) for d in dev]) for s, dev in self.dev_vs_stride],
                        "best_strides": float(best_stride),
                        "best_devs": float(best_dev),
                        "bool_masks": [_mask_info(self.bool_masks[0])]
                    }, f, indent=4)
        if return_figs:
            return strides_arr, devs_arr, best_stride, figs
        return strides_arr, devs_arr, best_stride

    def bedmesh_plot(self, ax):
        # Helper to plot bedmesh layers consistently
        self.bed_mesh.plot(keyword="deposition", ax=ax)
        self.bed_mesh.plot(keyword="boxes", ax=ax)

    def plot_status(self):
        """Plot the current status of the bed mesh and serpentine, overlapping all elements."""
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots()

        # Plot bedmesh deposition as a colored mesh
        self.bedmesh_plot(ax)

        # Draw the single squared serpentine
        self.serpentine.draw(ax=ax)

        print(f"Current stride: {self.serpentine.stride}, margin: {self.serpentine.margin}")
        plt.show()

    def _ensure_interactive_backend(self):
        """Attempt to switch to an interactive matplotlib backend if a non-interactive one is active."""
        import matplotlib
        backend = str(matplotlib.get_backend()).lower()
        if 'agg' in backend or 'pdf' in backend or 'svg' in backend:
            for candidate in ('QtAgg', 'Qt5Agg', 'TkAgg', 'MacOSX'):
                try:
                    matplotlib.use(candidate, force=True)
                    break
                except Exception:
                    continue
