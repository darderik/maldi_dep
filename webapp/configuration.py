import streamlit as st
from wrapper.Config import Config
from wrapper.MaldiStatus import MaldiStatus

st.set_page_config(page_title="Configuration", page_icon="⚙️", layout="wide")

st.title("⚙️ Configuration")
st.markdown("---")

# Initialize MaldiStatus in session state if not present
if 'ms' not in st.session_state:
    st.session_state.ms = MaldiStatus()

config = Config()

st.header("🔧 Machine Settings")
st.markdown("Configure machine parameters for the MALDI preparation process.")
col1, col2 = st.columns(2)
with col1:
    speed = st.number_input("Speed (mm/s)", value=float(config.get("speed")), step=1.0, help="Movement speed")
    acceleration = st.number_input("Acceleration (mm/s²)", value=float(config.get("acceleration")), step=10.0, help="Movement acceleration")
    nozzle_temp = st.number_input("Nozzle Temperature (°C)", value=float(config.get("nozzle_temperature")), step=10.0, help="Temperature of the nozzle")
    bed_temp = st.number_input("Bed Temperature (°C)", value=float(config.get("bed_temperature")), step=5.0, help="Temperature of the bed")
with col2:
    z_height = st.number_input("Z Height (mm)", value=float(config.get("z_height")), step=0.1, help="Z-axis height for movements")
    bed_size = st.number_input("Bed Size (mm)", value=float(config.get("bed_size_mm")), step=10.0, help="Size of the bed")
    max_speed = st.number_input("Max Speed (mm/s)", value=float(config.get("max_speed")), step=10.0, help="Maximum allowed speed")

st.markdown("---")
st.header("🧪 Simulation Settings")
st.markdown("Configure simulation parameters for optimization.")
col3, col4 = st.columns(2)
with col3:
    grid_step = st.number_input("Grid Step (mm)", value=float(config.get("grid_step")), step=0.1, min_value=0.1, help="Step size for simulation grid")
    min_stride = st.number_input("Minimum Stride (mm)", value=float(config.get("minimum_stride")), step=0.1, help="Minimum stride for optimization")
    max_stride = st.number_input("Maximum Stride (mm)", value=float(config.get("maximum_stride")), step=0.5, help="Maximum stride for optimization")
with col4:
    stride_steps = st.number_input("Stride Steps", value=int(config.get("stride_steps")), step=1, min_value=1, help="Number of stride steps to evaluate")
    x_points = st.number_input("X Points", value=int(config.get("x_points")), step=1, help="Number of points in X direction")
    passes = st.number_input("Passes", value=int(config.get("passes")), step=1, min_value=1, help="Number of passes for deposition")
st.markdown("---")
# Update config
col_btn1, col_btn2 = st.columns(2)
with col_btn1:
    if st.button("💾 Update Configuration", type="primary", use_container_width=True):
        config.set("speed", speed)
        config.set("acceleration", acceleration)
        config.set("nozzle_temperature", nozzle_temp)
        config.set("bed_temperature", bed_temp)
        config.set("z_height", z_height)
        config.set("bed_size_mm", bed_size)
        config.set("max_speed", max_speed)
        config.set("grid_step", grid_step)
        config.set("minimum_stride", min_stride)
        config.set("maximum_stride", max_stride)
        config.set("stride_steps", int(stride_steps))
        config.set("x_points", int(x_points))
        config.set("passes", int(passes))
        st.success("✅ Configuration updated successfully!")
        st.session_state.ms.refresh_bed_mesh()


