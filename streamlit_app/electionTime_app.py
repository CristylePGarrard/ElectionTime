import streamlit as st

# Define the pages
main_page = st.Page("pages/main_page.py", title="Home", icon="🏠")
page_2 = st.Page("pages/page_2.py", title="Representatives", icon="❄️")
page_3 = st.Page("pages/page_3.py", title="Page 3", icon="🎉")

# Set up navigation
pg = st.navigation([main_page, page_2, page_3])

st.write("# Welcome to the ElectionTime App! 👋")

# Run the selected page
pg.run()