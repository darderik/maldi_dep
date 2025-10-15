"""
MALDI Sample Preparation - Configuration Page

View and edit system configuration parameters.
"""

import streamlit as st
import sys
from pathlib import Path
import json

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from wrapper.Config import Config

st.title("⚙️ Configuration")
st.markdown("---")

# Get config singleton
config = Config()

# Load current config
def load_config():
    try:
        config._load_config()  # Reload from file
        return True
    except Exception as e:
        st.error(f"Error loading config: {e}")
        return False

# Save config (now handled by Config singleton automatically)
def save_config():
    try:
        config._save_config()
        st.success("Configuration saved successfully!")
        return True
    except Exception as e:
        st.error(f"Error saving config: {e}")
        return False

# Load/Save buttons
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("📁 Reload from config.json", type="primary"):
        if load_config():
            st.rerun()

with col2:
    if st.button("💾 Save Changes"):
        save_config()

with col3:
    if st.button("🔄 Reset to Defaults"):
        default_config = {
            'bed_size': 200,
            'z_height': 70,
            'speed': 2.0,
            'grid_step': 0.4,
            'spray_function': 'gaussian',
            'spray_radius_vs_z': [[30,20,10,5,70,40], [4,3,2,1,8,5]],
            'samples': [],
            'nozzle_temperature': 100.0,
            'bed_temperature': 40.0
        }
        config.update(default_config)
        st.success("Reset to defaults!")
        st.rerun()

st.markdown("---")

# Basic Parameters
st.header("Basic Parameters")

col1, col2 = st.columns(2)

with col1:
    bed_size = st.number_input(
        "Bed Size (mm)",
        min_value=50.0,
        max_value=500.0,
        value=float(config.get('bed_size') or 200),
        step=10.0
    )
    z_height = st.number_input(
        "Z Height (mm)",
        min_value=5.0,
        max_value=200.0,
        value=float(config.get('z_height') or 70),
        step=5.0
    )
    nozzle_temperature = st.number_input(
        "Nozzle Temperature (°C)",
        min_value=0.0,
        max_value=300.0,
        value=float(config.get('nozzle_temperature') or 100.0),
        step=1.0
    )

with col2:
    speed = st.number_input(
        "Speed (mm/s)",
        min_value=0.1,
        max_value=100.0,
        value=float(config.get('speed') or 2.0),
        step=0.1
    )
    grid_step = st.number_input(
        "Grid Step (mm)",
        min_value=0.1,
        max_value=5.0,
        value=float(config.get('grid_step') or 0.4),
        step=0.1
    )
    bed_temperature = st.number_input(
        "Bed Temperature (°C)",
        min_value=0.0,
        max_value=100.0,
        value=float(config.get('bed_temperature') or 40.0),
        step=1.0
    )

# Update config with new values
config.set('bed_size', bed_size)
config.set('z_height', z_height)
config.set('speed', speed)
config.set('grid_step', grid_step)
config.set('nozzle_temperature', nozzle_temperature)
config.set('bed_temperature', bed_temperature)

st.markdown("---")

# Spray Function Configuration
st.header("Spray Function")

spray_function = st.selectbox(
    "Spray Function Type",
    ["gaussian", "uniform", "custom"],
    index=["gaussian", "uniform", "custom"].index(config.get('spray_function') or 'gaussian')
)

config.set('spray_function', spray_function)

st.subheader("Spray Radius vs Z-Height Calibration")
st.caption("Define the relationship between z-height and spray radius")

# Get current spray data
spray_data = config.get('spray_radius_vs_z') or [[30,20,10,5,70,40], [4,3,2,1,8,5]]
z_values = spray_data[0] if len(spray_data) > 0 else [30,20,10,5,70,40]
radius_values = spray_data[1] if len(spray_data) > 1 else [4,3,2,1,8,5]

col1, col2 = st.columns(2)

with col1:
    z_input = st.text_input(
        "Z Heights (comma-separated)",
        value=", ".join([str(x) for x in z_values])
    )

with col2:
    radius_input = st.text_input(
        "Spray Radii (comma-separated)",
        value=", ".join([str(x) for x in radius_values])
    )

# Parse and update spray data
try:
    parsed_z = [float(x.strip()) for x in z_input.split(',') if x.strip()]
    parsed_radius = [float(x.strip()) for x in radius_input.split(',') if x.strip()]
    if len(parsed_z) == len(parsed_radius):
        config.set('spray_radius_vs_z', [parsed_z, parsed_radius])
        st.success(f"Calibration data updated: {len(parsed_z)} points")
    else:
        st.error("Z-heights and radii must have the same number of values")
except ValueError as e:
    st.error(f"Invalid number format: {e}")

st.markdown("---")

# Samples Preview
st.header("Samples Configuration")

samples = config.get('samples') or []
st.write(f"**Total Samples:** {len(samples)}")

if samples:
    for i, sample in enumerate(samples):
        with st.expander(f"Sample {i+1}: {sample.get('type', 'unknown')}"):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"**Position:** {sample.get('position', 'N/A')}")
                st.write(f"**Size:** {sample.get('size', 'N/A')}")
            with col2:
                st.write(f"**Margin:** {sample.get('margin', 'N/A')} mm")
                st.write(f"**X Amount:** {sample.get('x_amount', 'N/A')}")
            with col3:
                st.write(f"**Strides:** {sample.get('strides', 'N/A')}")
                st.write(f"**Passes:** {sample.get('passes', 'N/A')}")
else:
    st.info("No samples defined. Go to the Samples page to add samples.")

st.markdown("---")

# Raw JSON Editor (Advanced)
st.header("Advanced: Raw JSON Editor")

with st.expander("⚠️ Edit Raw JSON (Advanced Users Only)"):
    st.warning("Editing the raw JSON can break the configuration. Use with caution!")

    json_text = st.text_area(
        "Configuration JSON",
        value=json.dumps(config.get_all(), indent=2),
        height=400
    )

    if st.button("Apply JSON Changes"):
        try:
            parsed_json = json.loads(json_text)
            config.update(parsed_json)
            st.success("JSON applied successfully!")
            st.rerun()
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON: {e}")

# Footer
st.markdown("---")
st.caption("Changes are automatically saved to config.json when modified.")
