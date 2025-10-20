# MALDI Sample Preparation Optimizer

A Python-based simulation and optimization tool for MALDI (Matrix-Assisted Laser Desorption/Ionization) sample preparation. This project optimizes deposition patterns using serpentine path planning to achieve uniform sample coverage across multiple deposition areas.

## Features

- **Bed Mesh System**: Define and manage deposition areas with boolean masks
- **Serpentine Path Planning**: Generate optimized squared serpentine patterns with configurable stride and margin
- **Multi-Pass Support**: Alternate direction passes for better coverage
- **Deposition Simulation**: Simulate the deposition process with real-time visualization
- **Stride Optimization**: Automatically find the optimal stride value that minimizes deposition standard deviation
- **G-code Generation**: Export optimized paths as G-code for 3D printer/CNC execution
- **Web Interface**: Streamlit-based web application for interactive configuration and visualization
- **Progress Tracking**: Real-time progress callbacks for long-running optimizations

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd MALDI
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Quick Start (Command Line)

```python
from meshing import BedMesh
from optimizer import SquaredSerpentine, Optimizer
import numpy as np

# Create bed mesh with a rectangular deposition area
bm = BedMesh(size_mm=235.0, grid_step_mm=0.1, spray_size=20.0)
bm.add_bool_mask(points=[(30.0, 50.0, 20.0, 40.0)], shape="rectangle")

# Create serpentine path planner
serp = SquaredSerpentine(
    bm=bm, 
    bool_mask=bm._bool_masks[0],
    margin=10.0,
    x_amnt=20,
    stride=4.0,
    passes=2
)

# Create optimizer and find best stride
opt = Optimizer(bedmesh=bm, serpentine=serp, verbose=True)
strides, devs, best_stride = opt.span_std_vs_stride(
    strides=np.linspace(1, 40, 10),
    save_to_json=True
)

print(f"Optimal stride: {best_stride:.3f} mm")
```

### Web Application

Launch the interactive web interface:

```bash
python run_webapp.py
```

Then open your browser to `http://localhost:8501` to access the Streamlit interface.

### Using the Wrapper API

For high-level operations, use the `MaldiStatus` wrapper:

```python
from wrapper.MaldiStatus import MaldiStatus, Config

# Configure parameters
Config().set("bed_size_mm", 235.0)
Config().set("minimum_stride", 1.0)
Config().set("maximum_stride", 10.0)
Config().set("passes", 2)

# Create status manager
ms = MaldiStatus()
ms.refresh_bed_mesh()

# Add deposition areas
ms.add_rectangle(30, 50, 20, 40)

# Optimize and generate G-code
ms.optimize_all_strides(visualize=True)
ms.export_gcode("output.gcode")
```

## Project Structure

```
MALDI/
├── meshing/           # Bed mesh and mask management
│   ├── BedMesh.py    # Main bed mesh class
│   ├── Mask.py       # Boolean and numeric masks
│   └── Nozzle.py     # Nozzle deposition model
├── optimizer/         # Path optimization
│   ├── Optimizer.py           # Stride optimization algorithms
│   └── SquaredSerpentine.py   # Serpentine path generator
├── simulation/        # Deposition simulation
│   └── Simulator.py  # Movement scheduler and simulator
├── gcode/            # G-code generation
│   └── GCodeCreator.py
├── wrapper/          # High-level API wrapper
│   └── MaldiStatus.py
├── webapp/           # Streamlit web interface
├── graphing/         # Visualization utilities
├── logs/             # Optimization results (JSON)
├── main.py           # Example usage scripts
├── run_webapp.py     # Web app launcher
└── requirements.txt  # Python dependencies
```

## Key Components

### BedMesh
Manages the deposition bed with configurable grid resolution. Supports multiple boolean masks for defining deposition areas.

### SquaredSerpentine
Generates serpentine movement patterns for each deposition area with:
- Configurable stride (spacing between lines)
- Margin expansion beyond mask boundaries
- Multi-pass support with alternating directions
- Automatic boundary clamping

### Optimizer
Performs stride optimization by:
1. Sweeping through a range of stride values
2. Simulating deposition for each stride
3. Computing standard deviation within masked areas
4. Identifying the stride with minimum deviation
5. Visualizing results and exporting data

### Scheduler
Simulates the deposition process by:
- Moving the nozzle through planned waypoints
- Applying deposition masks at each position
- Tracking cumulative deposition over time
- Providing real-time visualization

## Configuration Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `bed_size_mm` | Size of the bed in millimeters | 235.0 |
| `grid_step_mm` | Grid resolution for simulation | 0.1 |
| `spray_size` | Nozzle spray diameter | 20.0 |
| `stride` | Spacing between serpentine lines | 4.0 |
| `margin` | Extension beyond mask boundaries | 10.0 |
| `x_amnt` | Number of points per horizontal line | 20 |
| `passes` | Number of deposition passes | 1 |
| `speed` | Movement speed (mm/s) | 5.0 |

## Output

### JSON Logs
Optimization results are saved to `logs/dev_vs_stride_<timestamp>.json`:
```json
{
  "dev_vs_stride": [[stride, deviation], ...],
  "best_strides": 3.456,
  "best_devs": 0.0123,
  "bool_masks": [...]
}
```

### G-code
Export optimized paths as G-code for execution on 3D printers or CNC machines.

## Dependencies

Core dependencies:
- **numpy**: Numerical computations
- **scipy**: Scientific computing and interpolation
- **matplotlib**: Visualization and plotting
- **streamlit**: Web application framework
- **tqdm**: Progress bars

See `requirements.txt` for complete list.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

### Development Setup

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Developed for MALDI sample preparation optimization
- Uses serpentine path planning for uniform coverage
- Inspired by 3D printing and CNC toolpath generation

## Contact

For questions or support, please open an issue in the repository.
