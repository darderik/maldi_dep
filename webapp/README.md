# MALDI Sample Preparation - Web Interface

A comprehensive web interface built with Streamlit for the MALDI sample preparation system.

## Features

- **🏠 Home**: Overview dashboard with system status and quick actions
- **⚙️ Configuration**: View and edit system parameters from config.json
- **🎯 Samples**: Manage sample regions and create serpentine patterns
- **🔬 Simulation**: Run stride optimization and view results
- **📝 G-Code**: Generate and download G-code files for CNC execution

## Installation

1. Install the required dependencies:
```bash
pip install -r webapp/requirements.txt
```

## Usage

### Quick Start
Run the web app launcher:
```bash
python run_webapp.py
```

Or manually run Streamlit:
```bash
cd webapp
streamlit run entry.py
```

The web app will open in your browser at `http://localhost:8501`

## Workflow

### 1. Home Dashboard
- View system status and current parameters
- Quick actions for common tasks
- Activity log

### 2. Configuration
- Load parameters from config.json
- Edit basic parameters (bed size, z-height, speed, grid step)
- Configure spray function and calibration data
- Save changes back to config.json

### 3. Samples
- Initialize system from configuration
- View current sample regions
- Add new rectangular samples
- Create serpentine patterns
- Remove samples if needed

### 4. Simulation
- Run stride optimization for uniform deposition
- Load previous optimization results
- Manually set stride values
- View optimization status and results

### 5. G-Code Generation
- Generate G-code from optimized parameters
- Preview generated G-code
- Download G-code files
- Generate with specific stride values
- View recent G-code files

## Configuration Format

The system uses a JSON configuration file (`config.json`) with the following structure:

```json
{
    "bed_size": 200,
    "z_height": 70,
    "spray_function": "gaussian",
    "spray_radius_vs_z": [[30,20,10,5,70,40], [4,3,2,1,8,5]],
    "speed": 2.0,
    "grid_step": 0.4,
    "samples": [
        {
            "type": "rectangle",
            "position": [40.0, 40.0],
            "size": [25.0, 25.0],
            "margin": 10.0,
            "x_amount": 20,
            "strides": [0.1, 10.0, 30],
            "passes": 4
        }
    ]
}
```

## Tips

- **Start Here**: Begin with the Home page to get an overview
- **Initialize First**: Always initialize the system before working with samples
- **Save Progress**: Save your configuration regularly in the Configuration page
- **Optimize Before G-Code**: Run optimization in the Simulation page before generating G-code
- **Check Status**: Use the status indicators on each page to ensure proper setup

## Troubleshooting

- **System not initialized**: Go to Samples page and click "Initialize from Config"
- **No serpentines created**: Click "Create Serpentines" in the Samples page
- **Optimization fails**: Check your sample configuration and stride ranges
- **G-code empty**: Ensure serpentines are created and strides are set
- **Plots not showing**: Optimization plots open in separate matplotlib windows

## File Structure

```
webapp/
├── entry.py              # Main app entry point with navigation
├── home.py               # Home dashboard
├── configuration.py      # Parameter editing
├── samples.py            # Sample management
├── simulation.py         # Optimization and simulation
├── gcode.py              # G-code generation and download
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## Notes

- All measurements are in millimeters (mm)
- Speed is in mm/s
- The system supports multiple samples on a single bed
- Optimization results are saved to the `logs` folder
- G-code files are saved in the project root directory
- Session state persists during the web app session

## Version

Version 1.0.0 - October 2025
