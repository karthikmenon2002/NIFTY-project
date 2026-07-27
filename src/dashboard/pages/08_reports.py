from urllib.request import Request, urlopen
import streamlit as st

from src.dashboard.utils.db import get_companies

st.set_page_config(page_title="Annual Reports", layout="wide")

companies = get_companies()
company_ids = companies["company_id"].tolist()
selected = st.selectbox("Company", company_ids)

years = [2019, 2020, 2021, 2022, 2023, 2024]
for year in years:
    url = f"https://www.bseindia.com/xml-data/corpfiling/AttachHis/{selected}_{year}.pdf"
    try:
        request = Request(url, method="HEAD")
        with urlopen(request, timeout=5) as response:
            available = response.status < 400
    except Exception:
        available = False

    if available:
        st.link_button(f"{year} annual report", url)
    else:
        st.markdown(f"{year}: :red[Report unavailable]")
