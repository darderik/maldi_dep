# Wrapper Class - Usage Guide

The `Wrapper` class provides a high-level abstraction for MALDI sample preparation workflows. It uses parameters from `config.json` and maintains a single `BedMesh` instance with serpentine patterns.

## Instance Variables

The wrapper automatically loads configuration from `config.json`:
- `bed_size`: Size of the bed in mm
- `z_height`: Height of the spray nozzle
- `speed`: Movement speed
- `grid_step`: Grid step size for the mesh
- `spray_function`: Type of spray function (e.g., "gaussian")
- `spray_radius_vs_z`: Relationship between spray radius and z-height

Internal state:
- `bed_mesh_instance`: The BedMesh object (created in `__init__`)
- `serpentines`: List of SquaredSerpentine objects
- `optimizers`: List of Optimizer objects

## API Methods

### 1. `load_samples()`
Load sample positions from `config.json` and add them as masks to the bed mesh.

```python
wrapper = Wrapper()
wrapper.load_samples()  # Reads from config.json "samples" field
```

### 2. `add_rectangle_mask(x_min, x_max, y_min, y_max)`
Manually add a rectangular mask to the bed mesh.

```python
wrapper.add_rectangle_mask(40.0, 190.0, 40.0, 190.0)
```

### 3. `create_serpentines(margin=10.0, x_amnt=20, stride=4.0, passes=2)`
Create serpentine patterns for all masks in the bed mesh. Uses the wrapper's configured speed.

```python
wrapper.create_serpentines(
    margin=10.0,
    x_amnt=20,
    stride=4.0,
    passes=2
)
```

### 4. `optimize_strides(strides_to_test=None, save_to_json=True, plot=True)`
Optimize serpentine strides and automatically apply the best values.

```python
import numpy as np

best_strides = wrapper.optimize_strides(
    strides_to_test=np.linspace(5, 10, 5),
    save_to_json=True,
    plot=True
)
```

### 5. `apply_strides(strides)`
Manually apply stride values to serpentines.

```python
wrapper.apply_strides([6.5, 7.0])  # Different stride per serpentine
# or
wrapper.apply_strides(6.5)  # Same stride for all
```

### 6. `load_strides_from_json(json_file=None)`
Load optimized stride values from a JSON file (uses most recent if not specified).

```python
strides = wrapper.load_strides_from_json()  # Auto-finds latest
wrapper.apply_strides(strides)
```

### 7. `generate_gcode(output_file="output.gcode")`
Generate G-code from the current serpentines.

```python
gcode_path = wrapper.generate_gcode("my_output.gcode")
print(f"G-code saved to: {gcode_path}")
```

## Complete Workflow Examples

### Example 1: Full Optimization Workflow

```python
from wrapper.Wrapper import Wrapper
import numpy as np

# Initialize wrapper (uses config.json)
wrapper = Wrapper()

# Add sample masks
wrapper.add_rectangle_mask(40.0, 190.0, 40.0, 190.0)

# Create serpentines
wrapper.create_serpentines(margin=10.0, x_amnt=20, stride=4.0, passes=2)

# Optimize strides
best_strides = wrapper.optimize_strides(
    strides_to_test=np.linspace(5, 10, 5),
    save_to_json=True,
    plot=True
)

# Generate G-code (strides already applied by optimize_strides)
gcode_file = wrapper.generate_gcode("optimized.gcode")
print(f"Generated: {gcode_file}")
```

### Example 2: Using Saved Optimization Results

```python
from wrapper.Wrapper import Wrapper

# Initialize wrapper
wrapper = Wrapper()

# Load samples from config
wrapper.load_samples()

# Create serpentines with initial stride
wrapper.create_serpentines(stride=4.0)

# Load previously optimized strides
strides = wrapper.load_strides_from_json()  # Finds latest JSON
wrapper.apply_strides(strides)

# Generate G-code
wrapper.generate_gcode("from_json.gcode")
```

### Example 3: Manual Control

```python
from wrapper.Wrapper import Wrapper

# Initialize with custom parameters
wrapper = Wrapper(bed_size=200.0, speed=50.0)

# Add multiple samples
wrapper.add_rectangle_mask(30.0, 50.0, 20.0, 40.0)
wrapper.add_rectangle_mask(70.0, 90.0, 60.0, 80.0)

# Create serpentines
wrapper.create_serpentines(margin=8.0, stride=5.5)

# Generate without optimization
wrapper.generate_gcode("manual.gcode")
```

## Benefits of This Design

1. **Uses instance state**: Single `bed_mesh_instance` created in `__init__`
2. **Configuration-driven**: Automatically loads from `config.json`
3. **Smaller, focused methods**: Each method does one thing well
4. **Chainable workflow**: Methods build on each other's state
5. **Flexible**: Can load samples from config or add manually
6. **Reusable**: Can regenerate G-code with different strides without recreating everything
