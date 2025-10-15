import numpy as np
import matplotlib
matplotlib.use('Agg')  # Ensure non-interactive backend
import matplotlib.pyplot as plt

from numpy import ndarray as NDArray
# Plot x y keeping their sequence using arrows


def plot_x_y_points(points: NDArray, show: bool = False):
    x = points[0, :]
    y = points[1, :]
    plt.quiver(x[:-1], y[:-1], x[1:] - x[:-1], y[1:] - y[:-1], angles='xy', scale_units='xy', scale=1)
    plt.xlim(x.min() - 1, x.max() + 1)
    plt.ylim(y.min() - 1, y.max() + 1)
    plt.grid()
    if show:
        plt.show()
