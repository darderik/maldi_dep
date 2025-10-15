"""
MALDI Sample Preparation - G-Code Generation Page

Generate and download G-code files for CNC execution.
"""

import streamlit as st
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from wrapper.Wrapper import Wrapper

st.title("📝 G-Code Generation")
st.markdown("---")

# Initialize session state
if 'wrapper' not in st.session_state:
    st.session_state.wrapper = None
if 'gcode_content' not in st.session_state:
    st.session_state.gcode_content = None
if 'gcode_filename' not in st.session_state:
    st.session_state.gcode_filename = None

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
    gcode_status = "✅ Generated" if st.session_state.gcode_content else "❌ Not Generated"
    st.metric("G-Code", gcode_status)

st.markdown("---")

if not st.session_state.wrapper:
    st.warning("⚠️ System not initialized. Go to Samples page and initialize the system first.")
    st.stop()

wrapper = st.session_state.wrapper

# G-Code Generation Section
st.header("🚀 Generate G-Code")

st.markdown("Generate G-code from the current serpentine patterns and stride settings.")

col1, col2 = st.columns(2)
if not st.session_state.gcode_filename:
    st.session_state.gcode_filename = f"maldi_{datetime.now().strftime('%Y%m%d_%H%M%S')}.gcode"
with col1:
    output_filename = st.text_input(
        "Output Filename",
        value=st.session_state.gcode_filename,
        help="Filename for the generated G-code file"
    )
    st.session_state.gcode_filename = output_filename

with col2:
    add_timestamp = st.checkbox("Add timestamp to filename", value=True)

# Generate filename with timestamp if requested
if add_timestamp and not output_filename.startswith('maldi_'):
    base_name = output_filename.replace('.gcode', '')
    output_filename = f"{base_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.gcode"

# Current stride status
st.subheader("Current Stride Settings")
if hasattr(wrapper, 'serpentines') and wrapper.serpentines:
    stride_info = []
    for idx, serp in enumerate(wrapper.serpentines):
        try:
            current_stride = serp.get_stride() if hasattr(serp, 'get_stride') else "Unknown"
            stride_info.append(f"Serpentine {idx + 1}: {current_stride} mm")
        except:
            stride_info.append(f"Serpentine {idx + 1}: Error retrieving stride")

    st.info(" | ".join(stride_info))
else:
    st.warning("No stride information available.")

# Generate button
if st.button("🚀 Generate G-Code", type="primary"):
    try:
        with st.spinner("Generating G-code..."):
            output_path = wrapper.generate_gcode(output_filename)

            # Read the generated file
            with open(output_path, 'r') as f:
                gcode_content = f.read()

            st.session_state.gcode_content = gcode_content
            st.session_state.gcode_filename = output_filename

            st.success(f"✅ G-code generated successfully: {output_filename}")

            # Statistics
            lines = gcode_content.split('\n')
            st.subheader("G-Code Statistics")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Lines", len(lines))
            with col2:
                st.metric("File Size", f"{len(gcode_content)} bytes")
            with col3:
                commands = [line for line in lines if line.strip() and not line.strip().startswith(';')]
                st.metric("G-Code Commands", len(commands))

    except Exception as e:
        st.error(f"❌ Error generating G-code: {str(e)}")
        st.exception(e)

# Specific Stride Generation
st.markdown("---")
st.header("🎯 Generate with Specific Stride")

st.markdown("Generate G-code using a specific stride value for all serpentines.")

col1, col2 = st.columns(2)

with col1:
    specific_stride = st.number_input(
        "Stride Value (mm)",
        min_value=0.1,
        max_value=50.0,
        value=1.0,
        step=0.1
    )

with col2:
    specific_filename = st.text_input(
        "Specific Filename",
        value=f"maldi_specific_{datetime.now().strftime('%Y%m%d_%H%M%S')}.gcode"
    )

if st.button("Generate with Specific Stride"):
    try:
        with st.spinner("Generating G-code with specific stride..."):
            output_path = wrapper.gcode_from_specific_stride(specific_stride, specific_filename)

            # Read the generated file
            with open(output_path, 'r') as f:
                gcode_content = f.read()

            st.session_state.gcode_content = gcode_content
            st.session_state.gcode_filename = specific_filename

            st.success(f"✅ G-code generated with stride {specific_stride} mm: {specific_filename}")

    except Exception as e:
        st.error(f"❌ Error generating G-code: {str(e)}")

# G-Code Preview and Download
if st.session_state.gcode_content:
    st.markdown("---")
    st.header("📄 G-Code Preview")

    # Preview controls
    col1, col2 = st.columns(2)

    with col1:
        preview_lines = st.slider(
            "Preview lines",
            min_value=10,
            max_value=200,
            value=50,
            step=10
        )

    with col2:
        show_comments = st.checkbox("Show comments", value=False)

    # Display preview
    lines = st.session_state.gcode_content.split('\n')

    if not show_comments:
        lines = [line for line in lines if not line.strip().startswith(';')]

    preview_content = '\n'.join(lines[:preview_lines])

    st.code(preview_content, language="gcode")

    # Download button
    st.download_button(
        label="📥 Download G-Code",
        data=st.session_state.gcode_content,
        file_name=st.session_state.gcode_filename,
        mime="text/plain",
        type="primary",
        width='stretch'
    )

    # Full content in expander
    with st.expander("View Full G-Code"):
        st.code(st.session_state.gcode_content, language="gcode")

# Recent G-Code Files
st.markdown("---")
st.header("📂 Recent G-Code Files")

# List .gcode files in the current directory
gcode_files = list(Path(".").glob("*.gcode"))
if gcode_files:
    gcode_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)  # Most recent first

    for gcode_file in gcode_files[:5]:  # Show last 5
        col1, col2, col3 = st.columns([3, 1, 1])

        with col1:
            st.write(f"📄 {gcode_file.name}")

        with col2:
            file_size = gcode_file.stat().st_size
            st.write(f"{file_size} bytes")

        with col3:
            if st.button(f"Load {gcode_file.name}", key=f"load_{gcode_file.name}"):
                try:
                    with open(gcode_file, 'r') as f:
                        content = f.read()
                    st.session_state.gcode_content = content
                    st.session_state.gcode_filename = gcode_file.name
                    st.success(f"Loaded {gcode_file.name}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error loading file: {e}")
else:
    st.info("No G-code files found in current directory.")

# Footer
st.markdown("---")
st.caption("G-code files are saved in the project root directory. Make sure to backup important files.")
