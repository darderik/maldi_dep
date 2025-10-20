import streamlit as st

st.set_page_config(page_title="Home", page_icon="🏠", layout="wide")

st.title("🔬 MALDI Sample Preparation")
st.markdown("---")

st.markdown("""
### Welcome to the MALDI Sample Preparation Web App!

This application helps you configure, simulate, and generate G-code for MALDI sample preparation.

#### 🚀 Getting Started:

1. **⚙️ Configuration**: Set up machine and simulation parameters
2. **🧫 Samples**: Add samples by specifying their position and size
3. **🔬 Simulation**: Optimize strides or run manual simulations
4. **📝 G-Code**: Generate G-code for your configured samples

#### 📖 Workflow:

1. Start by configuring your machine settings in the **Configuration** page
2. Add samples in the **Samples** page
3. Run optimizations or simulations in the **Simulation** page
4. Generate and download G-code in the **G-Code** page

---

Use the navigation menu on the left to get started!
""")
