import streamlit as st

def reset():
    st.session_state.setdefault("question_index", 0)
    st.session_state.setdefault("gaps", {})
    st.session_state.setdefault("done_steps", set())
    st.session_state.setdefault("chat", [])

