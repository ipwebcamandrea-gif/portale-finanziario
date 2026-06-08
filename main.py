import streamlit as st

def check_password():
    if "password_correct" not in st.session_state:
        st.title("Accesso Protetto")
        st.text_input("Password:", type="password", key="pwd_input")
        if st.button("Accedi"):
            if st.session_state["pwd_input"] == st.secrets["PASSWORD"]:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("Password errata")
        return False
    return st.session_state["password_correct"]

if check_password():
    st.set_page_config(layout="wide")
    pg = st.navigation([
        st.Page("pagine/dashboard.py", title="Dashboard Watchlist"),
        st.Page("pagine/grafico.py", title="Analisi Grafica")
    ])
    pg.run()