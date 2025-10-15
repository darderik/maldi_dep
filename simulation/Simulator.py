from dataclasses import dataclass
from numpy import ndarray as NDArray
import numpy as np
from typing import Optional, Tuple, List
from meshing import BedMesh
from tqdm import tqdm


@dataclass
class Movement:
    """Class representing a movement in the bed mesh."""
    x: float
    y: float
    speed: float = 0.0
    acceleration: float = 0.0

    def __post_init__(self):
        """Post-initialization to ensure all values are floats."""
        self.x = float(self.x)
        self.y = float(self.y)
        self.speed = float(self.speed)
        self.acceleration = float(self.acceleration)


class Scheduler:
    """
    Scheduler simulates the movement of a nozzle over a bed mesh, controlling the deposition process
    by executing a sequence of movements at specified speeds.

    Attributes:
        bed (BedMesh): The mesh representing the bed where deposition occurs.
        current_position (Tuple[float, float]): The current (x, y) position of the nozzle.
        movement_list (List[Movement]): List of movements to execute, each with target position and speed.
        current_speed (float): The current speed of the nozzle.
        current_time (float): The current simulation time.
        min_time_step (float): The minimum allowed time step for simulation.
    """

    def __init__(self, bed: BedMesh, mov_list: List[Movement], min_time_step: float = 0.1):
        """
        Initialize the Scheduler.

        Args:
            bed (BedMesh): The mesh representing the bed for deposition.
            x_y_speed (NDArray): Array of movements, each containing (x, y, speed).
            min_time_step (float, optional): Minimum allowed time step for simulation. Defaults to 0.1.
        """
        self.bed = bed
        self.current_position: Tuple[float, float] = (0.0, 0.0)
        self.movement_list: List[Movement] = []
        self.current_speed: float = 0
        self.movement_list = mov_list
        self.current_time: float = 0.0
        self.min_time_step: float = min_time_step
        # Track segments for live plotting: list of ((x0,y0), (x1,y1))
        self._segments: List[Tuple[Tuple[float, float], Tuple[float, float]]] = []

    def start(self, live_plot: bool = False, refresh_every: int = 1):
        """
        Execute the scheduled movements, simulating nozzle deposition over the bed mesh.

        If live_plot is True, shows an updating figure with:
          - Deposition map with boolean mask bounding boxes
          - Concatenated arrows representing movements executed so far

        Args:
            live_plot (bool): Enable live plotting of the simulation. Defaults to False.
            refresh_every (int): Redraw frequency in number of high-level movements. Defaults to 1.
        """
        fig = ax = None
        total_moves = len(self.movement_list)
        if live_plot:
            # reset segments for a fresh session
            self._segments = []
            fig, ax = self._init_live_plot()

        for idx, movement in enumerate(tqdm(self.movement_list, desc="Simulating movements", unit="move")):
            old_x = self.current_position[0]
            old_y = self.current_position[1]
            old_speed = self.current_speed

            x = movement.x
            y = movement.y
            speed = movement.speed
            step = self.bed.grid_step_mm

            distance = np.sqrt((x - old_x) ** 2 + (y - old_y) ** 2)
            time_duration = distance / speed if speed != 0 else 0.0
            x_distance = x - old_x
            y_distance = y - old_y
            if (distance < step):
                # If the distance is less than a step, just spray at the current position
                self.bed._nozzle.spray(apply_position=(old_x, old_y))
                # Track trivial move for plotting
                if live_plot:
                    self._segments.append(((old_x, old_y), (old_x, old_y)))
                    if (idx % max(1, refresh_every) == 0) or (idx == total_moves - 1):
                        self._refresh_live_plot(ax)
                continue
            distance = np.sqrt(x_distance ** 2 + y_distance ** 2)
            # Calculate speed for even steps x y
            if time_duration == 0:
                x_speed = 0.0
                y_speed = 0.0
            else:
                x_speed = x_distance / time_duration
                y_speed = y_distance / time_duration

            time_steps_count = int(distance / step) if int(distance /
                                                           step) > self.min_time_step else int(distance / self.min_time_step)
            time_steps = np.linspace(self.current_time, self.current_time + time_duration, max(1, time_steps_count))
            # Check error ?
            for t in time_steps:
                old_x = self.current_position[0]
                old_y = self.current_position[1]
                time_incr = t - self.current_time
                if time_incr > 0:
                    self.current_position = (old_x + x_speed * time_incr,
                                             old_y + y_speed * time_incr)
                    self.bed._nozzle.spray(apply_position=self.current_position, time=time_incr)
                    self.current_time = t

            # After completing this high-level movement, record the segment and refresh if needed
            if live_plot:
                self._segments.append(((old_x, old_y), (self.current_position[0], self.current_position[1])))
                if (idx % max(1, refresh_every) == 0) or (idx == total_moves - 1):
                    self._refresh_live_plot(ax)

        # Ensure final plot is up-to-date
        if live_plot:
            self._refresh_live_plot(ax)

    def _init_live_plot(self):
        """Initialize the live plot figure and axis in interactive mode with persistent artists."""
        import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle
        from scipy.ndimage import label as ndimage_label, find_objects
        plt.ion()
        fig, ax = plt.subplots()

        # Compute padded extent to align pixel centers
        dx = float(self.bed.grid_step_mm)
        extent = (-dx / 2.0, self.bed.size_mm + dx / 2.0, -dx / 2.0, self.bed.size_mm + dx / 2.0)

        # Base image (deposition)
        im = ax.imshow(self.bed.deposition_mesh, extent=extent, origin='lower')
        cb = fig.colorbar(im, ax=ax, label='Intensity')

        # Static boolean mask bounding boxes (computed once)
        bool_mesh = np.asarray(self.bed.bool_mesh, dtype=bool)
        result = ndimage_label(bool_mesh)
        labeled = result[0] if isinstance(result, tuple) else result
        step = self.bed.grid_step_mm
        self._box_patches = []
        for sl in find_objects(labeled):
            if sl is None:
                continue
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
            self._box_patches.append(rect)

        # Quiver for path arrows (start empty, updated later)
        self._qv = ax.quiver([], [], [], [], angles='xy', scale_units='xy', scale=1, color='cyan', alpha=0.9)
        self._qv_count = 0

        # Current position marker
        (pos_pt,) = ax.plot([self.current_position[0]], [self.current_position[1]],
                            marker='o', color='black', markersize=4, linestyle='')
        self._pos_pt = pos_pt

        ax.set_title('Live Simulation')
        ax.set_xlabel('X (mm)')
        ax.set_ylabel('Y (mm)')
        ax.grid(True, linestyle='--', alpha=0.3)
        ax.set_aspect('equal', adjustable='box')
        # Lock limits to padded extent to avoid zoom drift
        ax.set_xlim(extent[0], extent[1])
        ax.set_ylim(extent[2], extent[3])

        fig.tight_layout()
        fig.canvas.draw()
        fig.canvas.flush_events()

        # Save handles for refresh
        self._fig = fig
        self._ax = ax
        self._im = im
        self._extent = extent
        return fig, ax

    def _refresh_live_plot(self, ax):
        """Update live plot artists without recreating axes or colorbars."""
        import matplotlib.pyplot as plt
        if ax is None:
            return
        # Update deposition image
        if hasattr(self, '_im') and self._im is not None:
            self._im.set_data(self.bed.deposition_mesh)
        # Update path arrows using quiver (filter zero-length segments)
        xs, ys, us, vs = [], [], [], []
        for (x0, y0), (x1, y1) in self._segments:
            dx = x1 - x0
            dy = y1 - y0
            if dx == 0 and dy == 0:
                continue
            xs.append(x0)
            ys.append(y0)
            us.append(dx)
            vs.append(dy)
        n = len(xs)
        if n == 0:
            # Ensure we don't keep stale arrows; recreate empty quiver if needed
            try:
                if self._qv is not None:
                    self._qv.remove()
            except Exception:
                pass
            self._qv = ax.quiver([], [], [], [], angles='xy', scale_units='xy', scale=1, color='cyan', alpha=0.9)
            self._qv_count = 0
        else:
            X0Y0 = np.column_stack([xs, ys])
            U = np.asarray(us)
            V = np.asarray(vs)
            if not hasattr(self, '_qv_count') or self._qv_count != n or self._qv is None:
                # Recreate quiver when arrow count changes to avoid matplotlib size mismatch
                try:
                    if self._qv is not None:
                        self._qv.remove()
                except Exception:
                    pass
                self._qv = ax.quiver(X0Y0[:, 0], X0Y0[:, 1], U, V, angles='xy',
                                     scale_units='xy', scale=1, color='cyan', alpha=0.9)
                self._qv_count = n
            else:
                self._qv.set_offsets(X0Y0)
                self._qv.set_UVC(U, V)
        # Update current position marker
        if hasattr(self, '_pos_pt') and self._pos_pt is not None:
            self._pos_pt.set_data([self.current_position[0]], [self.current_position[1]])
        # Keep limits/aspect fixed
        ax.set_xlim(self._extent[0], self._extent[1])
        ax.set_ylim(self._extent[2], self._extent[3])
        ax.set_aspect('equal', adjustable='box')
        # Redraw
        ax.figure.canvas.draw()
        ax.figure.canvas.flush_events()
        plt.pause(0.001)

    def plot(self, keyword: str = "deposition") -> None:
        """
        Plot the current state of the bed mesh.

        Args:
            keyword (str, optional): Type of plot to generate. Defaults to "deposition".
                - "deposition": Plots the deposition mesh.

        Raises:
            ValueError: If an unknown keyword is provided.
        """
        if keyword == "deposition":
            self.bed.plot()
        else:
            raise ValueError("Unknown keyword for plotting")
