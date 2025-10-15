import streamlit as st

page_array = [
    st.Page(page="home.py", title="Home"),
    st.Page(page="configuration.py", title="Configuration"),
    st.Page(page="samples.py", title="Samples"),
    st.Page(page="simulation.py", title="Simulation"),
    st.Page(page="gcode.py", title="G-Code"),
]
st.set_page_config(page_title="MALDI Sample Preparation", page_icon="🔬", layout="wide")
pg = st.navigation(page_array)
pg.run()