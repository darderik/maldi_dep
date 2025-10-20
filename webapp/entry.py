import streamlit as st

page_array = [
    st.Page(page="home.py", title="Home", icon="🏠"),
    st.Page(page="configuration.py", title="Configuration", icon="⚙️"),
    st.Page(page="samples.py", title="Samples", icon="🧫"),
    st.Page(page="simulation.py", title="Simulation", icon="🔬"),
    st.Page(page="gcode.py", title="G-Code", icon="📝"),
]
st.set_page_config(page_title="MALDI Sample Preparation", page_icon="🔬", layout="wide")
pg = st.navigation(page_array)
pg.run()