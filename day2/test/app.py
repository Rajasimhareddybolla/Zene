import streamlit as st

# Title
st.title("📜 Chola Dynasty - HTML Viewer")

# Load and display the HTML file
with open("index.html", "r", encoding="utf-8") as file:
    html_content = file.read()

st.subheader("📄 Static HTML File")
st.components.v1.html(html_content, height=500, scrolling=True)

# User Input for Custom HTML
st.subheader("✍️ Enter Custom HTML")
user_html = st.text_area("Write your own HTML code:", height=200)

if st.button("Render HTML"):
    st.components.v1.html(user_html, height=500, scrolling=True)
