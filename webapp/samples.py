import streamlit as st
from wrapper.MaldiStatus import MaldiStatus
from wrapper import SampleConfig
from wrapper.Config import Config

st.set_page_config(page_title="Samples", page_icon="🧫", layout="wide")

st.title("🧫 Samples")
st.markdown("---")

# Initialize MaldiStatus in session state if not present
if 'ms' not in st.session_state:
    st.session_state.ms = MaldiStatus()

ms = st.session_state.ms
config = Config()

st.header("➕ Add Sample")
st.markdown("Specify the position and dimensions of a new sample.")
col1, col2, col3 = st.columns(3)
with col1:
    bl_x = st.number_input("Bottom Left X (mm)", value=10.0, step=1.0, help="X coordinate of bottom-left corner")
    bl_y = st.number_input("Bottom Left Y (mm)", value=10.0, step=1.0, help="Y coordinate of bottom-left corner")
with col2:
    x_size = st.number_input("X Size (mm)", value=20.0, step=1.0, min_value=1.0, help="Width of the sample")
    y_size = st.number_input("Y Size (mm)", value=30.0, step=1.0, min_value=1.0, help="Height of the sample")
with col3:
    margin = st.number_input("Margin (mm)", value=float(config.get("margin")), step=0.5, help="Margin around the sample")
    passes = st.number_input("Passes", value=int(config.get("passes")), step=1, min_value=1, help="Number of passes")
    alternate_offset = st.checkbox("Alternate Offset", value=False, help="Use alternate offset for serpentine")
if st.button("➕ Add Sample", type="primary", use_container_width=True):
    new_sample = SampleConfig({
        "bl_corner": (bl_x, bl_y),
        "x_size": x_size,
        "y_size": y_size,
        "alternate_offset": alternate_offset,
        "margin": margin,
        "passes": passes,
    })
    ms.add_sample(new_sample)
    st.success(f"✅ Sample added at ({bl_x}, {bl_y}) with size {x_size}x{y_size} mm")
    st.rerun()

st.markdown("---")
st.header("📋 Current Samples")
samples_info = ms.get_samples_info()
if samples_info:
    for i, info in enumerate(samples_info):
        with st.expander(f"Sample {i+1}", expanded=True):
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("Bottom Left Corner", f"({info['bl_corner'][0]:.1f}, {info['bl_corner'][1]:.1f})")
            with col_b:
                st.metric("Size (X × Y)", f"{info['x_size']:.1f} × {info['y_size']:.1f} mm")
else:
    st.info("ℹ️ No samples added yet. Add a sample above to get started.")
