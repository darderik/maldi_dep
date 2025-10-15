"""
MALDI Sample Preparation - Samples Page

Manage sample regions and serpentine patterns.
"""

import streamlit as st
import sys
from pathlib import Path
import json

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from wrapper.Wrapper import Wrapper
from wrapper.Config import Config

st.title("🎯 Samples")
st.markdown("---")

# Initialize session state
if 'wrapper' not in st.session_state:
    st.session_state.wrapper = None
if 'samples_created' not in st.session_state:
    st.session_state.samples_created = False

# System status
col1, col2 = st.columns(2)

with col1:
    wrapper_status = "✅ Initialized" if st.session_state.wrapper else "❌ Not Initialized"
    st.metric("Wrapper Status", wrapper_status)

with col2:
    if st.session_state.wrapper:
        sample_count = len(st.session_state.wrapper.samples) if hasattr(st.session_state.wrapper, 'samples') else 0
        serp_count = len(st.session_state.wrapper.serpentines) if hasattr(st.session_state.wrapper, 'serpentines') else 0
        st.metric("Samples/Serpentines", f"{sample_count}/{serp_count}")
    else:
        st.metric("Samples/Serpentines", "0/0")

st.markdown("---")

# Initialize/Load section
st.header("System Initialization")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("⚙️ Initialize from Config", type="primary"):
        try:
            st.session_state.wrapper = Wrapper()
            st.session_state.samples_created = False
            st.success("System initialized from config!")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

with col3:
    if st.button("🗑️ Clear All"):
        st.session_state.wrapper = None
        st.session_state.samples_created = False
        st.success("System cleared!")

st.markdown("---")

# Current samples display
if st.session_state.wrapper:
    st.header("Current Samples")

    wrapper = st.session_state.wrapper

    if wrapper.samples:
        for idx, sample in enumerate(wrapper.samples):
            with st.expander(f"Sample {idx + 1}: {sample.get('type', 'Unknown')}", expanded=(idx==0)):
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.write("**Basic Info:**")
                    st.write(f"- **Position:** {sample.get('position', 'N/A')}")
                    st.write(f"- **Size:** {sample.get('size', 'N/A')}")
                    st.write(f"- **Type:** {sample.get('type', 'N/A')}")

                with col2:
                    st.write("**Pattern Parameters:**")
                    st.write(f"- **Margin:** {sample.get('margin', 'N/A')} mm")
                    st.write(f"- **X Amount:** {sample.get('x_amount', 'N/A')}")
                    st.write(f"- **Passes:** {sample.get('passes', 'N/A')}")

                with col3:
                    st.write("**Optimization Range:**")
                    strides = sample.get('strides', [])
                    if isinstance(strides, list) and len(strides) >= 3:
                        st.write(f"- **Stride Min:** {strides[0]} mm")
                        st.write(f"- **Stride Max:** {strides[1]} mm")
                        st.write(f"- **Steps:** {strides[2]}")
                    else:
                        st.write("- **Strides:** N/A")
    else:
        st.info("No samples loaded. Add samples below or load from config.json.")

    st.markdown("---")

    # Add new sample
    st.header("Add New Sample")

    with st.form("add_sample_form"):
        col1, col2 = st.columns(2)

        with col1:
            sample_type = st.selectbox("Sample Shape", ["rectangle"])
            bed_size_val = float(wrapper.bed_size) if wrapper.bed_size else 200.0
            pos_x = st.number_input("Position X (mm)", min_value=0.0, max_value=bed_size_val, value=40.0, step=1.0)
            pos_y = st.number_input("Position Y (mm)", min_value=0.0, max_value=bed_size_val, value=40.0, step=1.0)

        with col2:
            size_x = st.number_input("Size X (mm)", min_value=1.0, max_value=bed_size_val, value=25.0, step=1.0)
            size_y = st.number_input("Size Y (mm)", min_value=1.0, max_value=bed_size_val, value=25.0, step=1.0)
            margin = st.number_input("Margin (mm)", min_value=0.0, max_value=50.0, value=10.0, step=1.0)

        col3, col4, col5 = st.columns(3)

        with col3:
            x_amount = st.number_input("X Amount", min_value=1, max_value=100, value=20)
        with col4:
            passes = st.number_input("Passes", min_value=1, max_value=20, value=4)
        with col5:
            stride_steps = st.slider("Stride Optimization Steps", min_value=5, max_value=100, value=30)

        st.subheader("Stride Range for Optimization")
        col6, col7 = st.columns(2)

        with col6:
            stride_min = st.number_input("Minimum Stride (mm)", min_value=0.1, max_value=50.0, value=0.1, step=0.1)
        with col7:
            stride_max = st.number_input("Maximum Stride (mm)", min_value=0.1, max_value=50.0, value=10.0, step=0.1)

        submitted = st.form_submit_button("➕ Add Sample", type="primary")

        if submitted:
            try:
                new_sample = {
                    "type": sample_type,
                    "position": [pos_x, pos_y],
                    "size": [size_x, size_y],
                    "margin": margin,
                    "x_amount": x_amount,
                    "strides": [stride_min, stride_max, stride_steps],
                    "passes": passes
                }

                if sample_type == "rectangle":
                    x_min, y_min = pos_x, pos_y
                    x_max, y_max = x_min + size_x, y_min + size_y
                    wrapper.bed_mesh_instance.add_bool_mask(
                        points=[[x_min, x_max, y_min, y_max]],
                        shape="rectangle"
                    )
                    wrapper.samples.append(new_sample)
                    st.success("✅ Sample added successfully!")
                    st.rerun()
                else:
                    st.error("❌ Only rectangle samples are currently supported.")
            except Exception as e:
                st.error(f"❌ Error adding sample: {str(e)}")

    # Remove samples
    st.markdown("---")
    st.header("Remove Samples")

    if wrapper.samples:
        sample_to_remove = st.selectbox(
            "Select sample to remove",
            [f"Sample {i+1}: {s.get('type')} at {s.get('position')}" for i, s in enumerate(wrapper.samples)]
        )

        if st.button("🗑️ Remove Selected Sample", type="secondary"):
            try:
                idx_to_remove = [f"Sample {i+1}: {s.get('type')} at {s.get('position')}" for i, s in enumerate(wrapper.samples)].index(sample_to_remove)
                wrapper.samples.pop(idx_to_remove)
                # Note: Removing from bed_mesh_instance is more complex, so we'll recreate it
                st.success(f"Sample {idx_to_remove + 1} removed. Recreate serpentines to update the mesh.")
            except Exception as e:
                st.error(f"Error removing sample: {e}")
    else:
        st.info("No samples to remove.")

else:
    st.warning("⚠️ System not initialized. Click 'Initialize from Config' to get started.")

# Footer
st.markdown("---")
st.caption("Samples are stored in the wrapper instance. Save configuration to persist changes.")
