import streamlit as st

st.set_page_config(page_title="Nifty 100 Analytics", layout="wide", initial_sidebar_state="expanded")

st.title("Nifty 100 Analytics")
st.sidebar.success("Choose a screen")

pages = [
    "Home",
    "Company Profile",
    "Screener",
    "Peer Comparison",
    "Trend Analysis",
    "Sector Analysis",
    "Capital Allocation",
    "Annual Reports",
]

selection = st.sidebar.radio("Navigation", pages)

if selection == "Home":
    st.switch_page("pages/01_home.py")
elif selection == "Company Profile":
    st.switch_page("pages/02_profile.py")
elif selection == "Screener":
    st.switch_page("pages/03_screener.py")
elif selection == "Peer Comparison":
    st.switch_page("pages/04_peers.py")
elif selection == "Trend Analysis":
    st.switch_page("pages/05_trends.py")
elif selection == "Sector Analysis":
    st.switch_page("pages/06_sectors.py")
elif selection == "Capital Allocation":
    st.switch_page("pages/07_capital.py")
elif selection == "Annual Reports":
    st.switch_page("pages/08_reports.py")
