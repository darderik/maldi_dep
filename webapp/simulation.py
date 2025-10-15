"""
MALDI Sample Preparation - Simulation Page

Run simulations and view optimization results.
"""

import streamlit as st
import sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')  # Set non-interactive backend for Streamlit
import matplotlib.pyplot as plt
# Make matplotlib figures larger and higher DPI so Streamlit doesn't render tiny images
from matplotlib import rcParams
rcParams["figure.dpi"] = 160
rcParams["savefig.dpi"] = 160
rcParams["figure.figsize"] = (10, 6)
import numpy as np
from datetime import datetime

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from wrapper.Wrapper import Wrapper

# Helper to consistently resize figures prior to st.pyplot so they render big enough
def _resize_fig(fig, width: float = 12.0, height: float | None = None, dpi: int = 160):
    try:
        if height is None:
            # Heuristic: scale height with number of axes if present
            n_axes = len(fig.get_axes())
            height = max(6.0, 3.0 * n_axes) if n_axes > 0 else 6.0
        fig.set_size_inches(width, height, forward=True)
        fig.set_dpi(dpi)
        try:
            fig.tight_layout()
        except Exception:
            pass
    except Exception:
        pass
    return fig

st.title("🔬 Simulation")
st.markdown("---")

# Initialize session state
if 'wrapper' not in st.session_state:
    st.session_state.wrapper = None
if 'simulation_results' not in st.session_state:
    st.session_state.simulation_results = None
if 'optimization_complete' not in st.session_state:
    st.session_state.optimization_complete = False
# Store latest figures to render them at the bottom (prevents tiny charts due to early page layout)
if 'latest_figs' not in st.session_state:
    st.session_state.latest_figs = []
if 'latest_fig_captions' not in st.session_state:
    st.session_state.latest_fig_captions = []

# System status
col1, col2, col3 = st.columns(3)

with col1:
    wrapper_status = "✅ Initialized" if st.session_state.wrapper else "❌ Not Initialized"
    st.metric("Wrapper Status", wrapper_status)

with col2:
    if st.session_state.wrapper:
        serp_count = len(st.session_state.wrapper.serpentines) if hasattr(st.session_state.wrapper, 'serpentines') else 0
        st.metric("Serpentines", serp_count)
    else:
        st.metric("Serpentines", "0")

with col3:
    opt_status = "✅ Complete" if st.session_state.optimization_complete else "❌ Not Run"
    st.metric("Optimization", opt_status)

st.markdown("---")

if not st.session_state.wrapper:
    st.warning("⚠️ System not initialized. Go to Samples page and initialize the system first.")
    st.stop()

wrapper: Wrapper = st.session_state.wrapper

# Optimization Section
st.header("🎯 Stride Optimization")

st.markdown("Optimize stride parameters for uniform deposition across all samples.")

col1, col2 = st.columns(2)

with col1:
    sample_idx = st.number_input(
        "Sample Index to Optimize",
        min_value=0,
        max_value=max(0, len(wrapper.samples) - 1) if wrapper.samples else 0,
        value=0,
        help="Index of the sample to optimize (0-based)"
    )

with col2:
    save_results = st.checkbox("Save results to JSON", value=True)
    plot_results = st.checkbox("Generate plots", value=True)

if st.button("🚀 Run Optimization", type="primary"):
    try:
        if len(wrapper.samples) == 0:
            st.error("❌ No samples available for optimization. Please add samples first.")
            st.stop()
        with st.spinner("Running optimization... This may take several minutes depending on the stride range."):
            result = wrapper.optimize_strides(
                sample_idx=sample_idx,
                save_to_json=save_results,
                plot=plot_results,
                return_figs=True
            )

            best_strides, figs = result

            if best_strides:
                st.session_state.simulation_results = best_strides
                st.session_state.optimization_complete = True
                st.success("✅ Optimization completed successfully!")

                # Display results
                st.subheader("Optimization Results")
                st.write("**Best stride values found:**")
                for idx, stride in enumerate(best_strides):
                    st.metric(f"Serpentine {idx + 1}", f"{stride:.4f} mm")

                # Store plots to render them at the bottom
                st.session_state.latest_figs = []
                st.session_state.latest_fig_captions = []
                if figs:
                    for i, fig in enumerate(figs):
                        if i == 0:
                            _resize_fig(fig, width=12, height=None, dpi=170)
                            st.session_state.latest_fig_captions.append("Deposition Standard Deviation vs Stride")
                        else:
                            _resize_fig(fig, width=12, height=9, dpi=170)
                            st.session_state.latest_fig_captions.append("Deposition Map for Best Stride")
                        st.session_state.latest_figs.append(fig)
            else:
                st.error("❌ Optimization failed to find best strides.")

    except Exception as e:
        st.error(f"❌ Error during optimization: {str(e)}")
        st.exception(e)

# Load Previous Results
st.markdown("---")
st.header("📂 Load Previous Optimization")

logs_path = Path(__file__).parent.parent / "logs"
if logs_path.exists():
    json_files = [f.name for f in logs_path.iterdir() if f.name.startswith('dev_vs_stride_') and f.name.endswith('.json')]

    if json_files:
        json_files.sort(reverse=True)  # Most recent first
        selected_file = st.selectbox("Select optimization result", json_files)

        if st.button("📂 Load Strides"):
            try:
                file_path = logs_path / selected_file
                strides = wrapper.load_strides_from_json(str(file_path))
                wrapper.apply_strides(strides)
                st.session_state.simulation_results = strides
                st.session_state.optimization_complete = True
                st.success(f"✅ Loaded strides: {strides}")
            except Exception as e:
                st.error(f"❌ Error loading strides: {str(e)}")
    else:
        st.info("No previous optimization results found in logs folder.")
else:
    st.info("Logs folder not found.")

# Manual Stride Setting
st.markdown("---")
st.header("🔧 Manual Stride Control")

col1, col2, col3 = st.columns(3)

with col1:
    manual_stride = st.number_input(
        "Manual Stride Value (mm)",
        min_value=0.1,
        max_value=50.0,
        value=1.0,
        step=0.1,
        help="Apply the same stride to all serpentines"
    )

with col2:
    apply_stride = st.button("Apply Manual Stride", type="secondary")

with col3:
    simulate_manual = st.checkbox("Simulate after applying", value=True, help="Run deposition simulation and show charts")

if apply_stride:
    try:
        if simulate_manual:
            with st.spinner("Running simulation with manual stride..."):
                fig = wrapper.simulate_manual_stride(manual_stride, return_fig=True)
                # Store to bottom renderer
                st.session_state.latest_figs = []
                st.session_state.latest_fig_captions = []
                if fig:
                    _resize_fig(fig, width=12, height=10, dpi=170)
                    st.session_state.latest_figs.append(fig)
                    st.session_state.latest_fig_captions.append(f"Deposition Map - Manual Stride: {manual_stride} mm")
                
                # Show statistics
                std_dev = wrapper.bed_mesh_instance.get_std_deviation(overall_dev=False)
                if isinstance(std_dev, (list, np.ndarray)):
                    st.write("**Deposition Standard Deviations:**")
                    for i, dev in enumerate(std_dev):
                        st.write(f"- Sample {i+1}: {dev:.4f}")
                else:
                    st.metric("Overall Deposition Std Dev", f"{std_dev:.4f}")
        else:
            wrapper.apply_strides([manual_stride])
            st.success(f"✅ Applied stride {manual_stride} mm to all serpentines")
        
        st.session_state.simulation_results = [manual_stride] * len(wrapper.serpentines)
        
        # Show updated stride chart
        fig_stride, ax_stride = plt.subplots()
        # Ensure bar chart is wide enough
        fig_stride.set_size_inches(10, 4)
        fig_stride.set_dpi(160)
        strides = [serp.get_stride() if hasattr(serp, 'get_stride') else 0 for serp in wrapper.serpentines]
        ax_stride.bar(range(1, len(strides) + 1), strides)
        ax_stride.set_xlabel("Serpentine Index")
        ax_stride.set_ylabel("Stride (mm)")
        ax_stride.set_title("Current Stride Values for Serpentines")
        # Store stride bar chart at bottom after the main figure (do not push it inline above)
        st.session_state.latest_figs.append(fig_stride)
        st.session_state.latest_fig_captions.append("Current Stride Values for Serpentines")
        
    except Exception as e:
        st.error(f"❌ Error applying manual stride: {str(e)}")

# Current Stride Status
st.markdown("---")
st.header("📊 Current Stride Status")

if hasattr(wrapper, 'serpentines') and wrapper.serpentines:
    stride_data = []
    for idx, serp in enumerate(wrapper.serpentines):
        try:
            current_stride = serp.get_stride() if hasattr(serp, 'get_stride') else "Unknown"
            stride_data.append({
                'Serpentine': idx + 1,
                'Current Stride': current_stride,
                'Sample': idx if idx < len(wrapper.samples) else "N/A"
            })
        except:
            stride_data.append({
                'Serpentine': idx + 1,
                'Current Stride': "Error",
                'Sample': idx if idx < len(wrapper.samples) else "N/A"
            })

    if stride_data:
        st.dataframe(stride_data, width='stretch')
else:
    st.info("No serpentines available.")

# Simulation Results Summary
if st.session_state.simulation_results:
    st.markdown("---")
    st.header("📈 Simulation Summary")

    results = st.session_state.simulation_results

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Optimized Serpentines", len(results))

    with col2:
        avg_stride = np.mean(results) if results else 0
        st.metric("Average Stride", f"{avg_stride:.3f} mm")

    with col3:
        range_stride = max(results) - min(results) if results else 0
        st.metric("Stride Range", f"{range_stride:.3f} mm")

    # Detailed results
    st.subheader("Detailed Results")
    for i, stride in enumerate(results):
        st.write(f"**Serpentine {i+1}:** {stride:.4f} mm")

# Bottom charts section (always render figures here to avoid cramped header layout)
st.markdown("---")
st.header("🖼️ Visualization")

if st.session_state.latest_figs:
    for fig, caption in zip(st.session_state.latest_figs, st.session_state.latest_fig_captions):
        st.pyplot(fig, use_container_width=True)
        if caption:
            st.caption(caption)
else:
    st.caption("Run an optimization or simulation to see charts here.")

# Footer
st.markdown("---")
st.caption("Optimization results are automatically applied to serpentines for G-code generation.")
