"""
MALDI Sample Preparation - Home Dashboard

Overview page showing current system status, parameters, and quick actions.
"""

import streamlit as st
import sys
from pathlib import Path
import json

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from wrapper.Wrapper import Wrapper
from wrapper.Config import Config

st.title("🔬 MALDI Sample Preparation System")
st.markdown("---")

# Initialize session state
if 'wrapper' not in st.session_state:
    st.session_state.wrapper = None
if 'config_loaded' not in st.session_state:
    st.session_state.config_loaded = False

# Quick Actions
st.header("🚀 Quick Actions")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("📁 Load Config", type="primary", width='stretch'):
        try:
            config = Config()
            st.session_state.config_loaded = True
            st.success("Config loaded!")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

with col2:
    if st.button("⚙️ Initialize System", width='stretch'):
        try:
            st.session_state.wrapper = Wrapper()
            st.success("System initialized!")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

with col3:
    if st.button("📝 Generate G-Code", width='stretch'):
        if st.session_state.wrapper:
            try:
                filename = f"maldi_output_{st.session_state.get('timestamp', 'default')}.gcode"
                output_path = st.session_state.wrapper.generate_gcode(filename)
                st.success(f"G-Code generated: {filename}")
                st.session_state.last_gcode = output_path
            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.error("Initialize system first")

st.markdown("---")

# Current Parameters
st.header("📊 Current Parameters")

if st.session_state.config_loaded:
    config = Config()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("System Settings")
        st.write(f"**Bed Size:** {config.get('bed_size', 'N/A')} mm")
        st.write(f"**Z Height:** {config.get('z_height', 'N/A')} mm")
        st.write(f"**Speed:** {config.get('speed', 'N/A')} mm/s")
        st.write(f"**Grid Step:** {config.get('grid_step', 'N/A')} mm")
        st.write(f"**Nozzle Temperature:** {config.get('nozzle_temperature', 'N/A')} °C")
        st.write(f"**Bed Temperature:** {config.get('bed_temperature', 'N/A')} °C")

    with col2:
        st.subheader("Spray Function")
        st.write(f"**Type:** {config.get('spray_function', 'N/A')}")
        spray_data = config.get('spray_radius_vs_z', [[], []])
        if spray_data and len(spray_data) == 2:
            st.write(f"**Z-Radius Points:** {len(spray_data[0])} calibration points")

    with col3:
        st.subheader("Samples")
        samples = config.get('samples', []) or []
        st.write(f"**Sample Count:** {len(samples)}")
        for i, sample in enumerate(samples):
            st.write(f"**Sample {i+1}:** {sample.get('type', 'unknown')} at {sample.get('position', 'N/A')}")
else:
    st.info("No configuration loaded. Click 'Load Config' to get started.")

st.markdown("---")

# System Status
st.header("🔧 System Status")

status_col1, status_col2, status_col3 = st.columns(3)

with status_col1:
    config_status = "✅ Loaded" if st.session_state.config_loaded else "❌ Not Loaded"
    st.metric("Configuration", config_status)

with status_col2:
    wrapper_status = "✅ Initialized" if st.session_state.wrapper else "❌ Not Initialized"
    st.metric("Wrapper", wrapper_status)

with status_col3:
    if st.session_state.wrapper:
        sample_count = len(st.session_state.wrapper.samples) if hasattr(st.session_state.wrapper, 'samples') else 0
        serpentine_count = len(st.session_state.wrapper.serpentines) if hasattr(st.session_state.wrapper, 'serpentines') else 0
        st.metric("Samples/Serpentines", f"{sample_count}/{serpentine_count}")
    else:
        st.metric("Samples/Serpentines", "0/0")

# Recent Activity
st.header("📋 Recent Activity")

if 'activity_log' not in st.session_state:
    st.session_state.activity_log = []

# Display recent activities
if st.session_state.activity_log:
    for activity in reversed(st.session_state.activity_log[-5:]):  # Show last 5
        st.write(f"• {activity}")
else:
    st.info("No recent activity. Start by loading configuration and initializing the system.")

# Footer
st.markdown("---")
st.caption("MALDI Sample Preparation System - Use the navigation menu to access detailed functionality")
