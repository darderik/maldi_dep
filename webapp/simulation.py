import streamlit as st
from wrapper.MaldiStatus import MaldiStatus
import matplotlib.pyplot as plt

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
        with st.spinner("🔄 Running optimization..."):
            best_strides = ms.optimize_strides(save_to_json=True, plot=False)
            st.session_state.best_strides = best_strides
        st.success(f"✅ Optimization complete! Best strides: {best_strides}")
        col_metrics = st.columns(len(best_strides))
        for i, (col, stride) in enumerate(zip(col_metrics, best_strides)):
            with col:
                st.metric(f"Sample {i+1} Optimal Stride", f"{stride:.3f} mm")

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
            with st.spinner("🔄 Running simulation..."):
                fig = ms.simulate_manual_stride(stride, return_fig=True)
            if fig:
                with col2:
                    st.pyplot(fig)
                    plt.close(fig)
            else:
                st.error("❌ Simulation failed.")
with col2:
    st.info("ℹ️ Click 'Run Simulation' to see the deposition pattern for the specified stride value.")
