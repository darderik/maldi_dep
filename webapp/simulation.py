import streamlit as st
from wrapper.MaldiStatus import MaldiStatus
import matplotlib.pyplot as plt
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from logging_config import get_logger

logger = get_logger("MALDI.WebApp.Simulation")

st.set_page_config(page_title="Simulation", page_icon="🔬", layout="wide")

st.title("🔬 Simulation")
st.markdown("---")

# Initialize MaldiStatus in session state if not present
if 'ms' not in st.session_state:
    st.session_state.ms = MaldiStatus()

ms = st.session_state.ms

st.header("🎯 Optimize Strides")
st.markdown("Automatically find the optimal stride values for all samples.")

# Store optimization results in session state
if 'best_strides' not in st.session_state:
    st.session_state.best_strides = None

if st.button("▶️ Run Optimization", type="primary", use_container_width=True):
    if not ms.samples:
        st.error("❌ No samples added. Please add samples first in the Samples page.")
    else:
        logger.info("User clicked 'Run Optimization' button")
        # Create a progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Define progress callback for Streamlit
        def update_progress(current, total):
            progress = current / total
            progress_bar.progress(progress)
            status_text.text(f"🔄 Running optimization... {current}/{total} iterations")
        
        try:
            logger.info(f"Starting optimization with {len(ms.samples)} sample(s)")
            best_strides = ms.optimize_strides(save_to_json=True, plot=False, progress_callback=update_progress)
            st.session_state.best_strides = best_strides
            progress_bar.empty()
            status_text.empty()
            logger.info(f"Optimization successful! Best strides: {best_strides}")
            st.success(f"✅ Optimization complete! Best strides: {best_strides}")
            col_metrics = st.columns(len(best_strides))
            for i, (col, stride) in enumerate(zip(col_metrics, best_strides)):
                with col:
                    st.metric(f"Sample {i+1} Optimal Stride", f"{stride:.3f} mm")
        except Exception as e:
            progress_bar.empty()
            status_text.empty()
            logger.error(f"Error during optimization: {str(e)}", exc_info=True)
            st.error(f"❌ Error during optimization: {e}")

# Show visualization if optimization has been run
if st.session_state.best_strides is not None:
    st.markdown("### 📊 Optimized Deposition Map")
    with st.spinner("🔄 Generating visualization..."):
        try:
            st.text("Ordered strides:")
            for stride in st.session_state.best_strides:
                st.text(f" - {stride:.3f} mm")
            fig = ms.visualize_optimized_samples(st.session_state.best_strides)
            st.pyplot(fig)
            plt.close(fig)
            # Add standard deviation metric
            if ms.bed_mesh is not None:
                std_devs = ms.bed_mesh.get_std_deviation(overall_dev=True)
                st.metric("Deposition Standard Deviation", f"{std_devs[0]:.3f}")
        except Exception as e:
            st.error(f"❌ Error generating visualization: {e}")

st.markdown("---")
st.header("🧪 Manual Simulation")
st.markdown("Test a specific stride value and visualize the deposition pattern.")
col1, col2 = st.columns([1, 3])
with col1:
    stride = st.number_input("Stride (mm)", value=2.0, step=0.1, min_value=0.1, help="Stride value to test")
    if st.button("▶️ Run Simulation", use_container_width=True):
        if not ms.samples:
            st.error("❌ No samples added. Please add samples first in the Samples page.")
        else:
            # Create a progress bar for manual simulation
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Define progress callback for Streamlit
            def update_sim_progress(current, total):
                progress = current / total
                progress_bar.progress(progress)
                status_text.text(f"🔄 Simulating... {current}/{total} movements")
            
            try:
                logger.info(f"Starting manual simulation with stride={stride:.3f}mm")
                fig = ms.simulate_manual_stride(stride, return_fig=True, progress_callback=update_sim_progress)
                progress_bar.empty()
                status_text.empty()
                logger.info(f"Manual simulation completed for stride={stride:.3f}mm")
                if fig:
                    with col2:
                        st.pyplot(fig)
                        plt.close(fig)
                else:
                    logger.warning("Manual simulation returned None figure")
                    st.error("❌ Simulation failed.")
            except Exception as e:
                progress_bar.empty()
                status_text.empty()
                logger.error(f"Error during manual simulation: {str(e)}", exc_info=True)
                st.error(f"❌ Error during simulation: {e}")
with col2:
    st.info("ℹ️ Click 'Run Simulation' to see the deposition pattern for the specified stride value.")
