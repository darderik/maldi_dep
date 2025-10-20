import streamlit as st
from wrapper.MaldiStatus import MaldiStatus

st.set_page_config(page_title="G-Code", page_icon="📝", layout="wide")

st.title("📝 G-Code Generation")
st.markdown("---")

# Initialize MaldiStatus in session state if not present
if 'ms' not in st.session_state:
    st.session_state.ms = MaldiStatus()

ms = st.session_state.ms

st.header("📄 Generate G-Code from Current Configuration")
st.markdown("Generate G-Code using the current stride values for all samples.")
output_file = st.text_input("Output File Name", value="output.gcode", help="Name of the G-Code file to generate")

if st.button("📝 Generate G-Code", type="primary", use_container_width=True):
    if not ms.samples:
        st.error("❌ No samples added. Please add samples first in the Samples page.")
    else:
        try:
            with st.spinner("🔄 Generating G-Code..."):
                file_path = ms.generate_gcode(output_file)
            st.success(f"✅ G-Code generated and saved to {file_path}")
            with open(file_path, "r") as f:
                gcode_content = f.read()
            st.download_button("⬇️ Download G-Code", gcode_content, file_name=output_file, mime="text/plain")
            with st.expander("📋 Preview G-Code"):
                st.code(gcode_content, language="gcode")
        except Exception as e:
            st.error(f"❌ Error generating G-Code: {e}")

st.markdown("---")
st.header("🎯 G-Code from Specific Stride")
st.markdown("Generate G-Code by specifying a custom stride value for all samples.")
col1, col2 = st.columns(2)
with col1:
    specific_stride = st.number_input("Stride (mm)", value=2.0, step=0.1, min_value=0.1, help="Custom stride value")
with col2:
    specific_file = st.text_input("Output File Name", value="output_specific.gcode", key="specific", help="Name of the G-Code file")

if st.button("📝 Generate from Specific Stride", use_container_width=True):
    if not ms.samples:
        st.error("❌ No samples added. Please add samples first in the Samples page.")
    else:
        try:
            with st.spinner("🔄 Generating G-Code..."):
                file_path = ms.gcode_from_specific_stride(specific_stride, specific_file)
            st.success(f"✅ G-Code generated and saved to {file_path}")
            with open(file_path, "r") as f:
                gcode_content = f.read()
            st.download_button("⬇️ Download G-Code", gcode_content, file_name=specific_file, key="download_specific", mime="text/plain")
            with st.expander("📋 Preview G-Code"):
                st.code(gcode_content, language="gcode")
        except Exception as e:
            st.error(f"❌ Error generating G-Code: {e}")
