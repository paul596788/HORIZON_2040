import streamlit as st


st.set_page_config(
    page_title="HORIZON 2040",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
section[data-testid="stSidebar"] {
    background:
        radial-gradient(720px 320px at 0% 0%, rgba(59, 130, 246, 0.12) 0%, rgba(59, 130, 246, 0) 48%),
        linear-gradient(180deg, #1d1f2a 0%, #141824 100%);
    border-right: 1px solid rgba(148, 163, 184, 0.12);
}

section[data-testid="stSidebar"] > div {
    background: transparent;
}

div[data-testid="stSidebarNav"] {
    background: rgba(255, 255, 255, 0.025);
    border: 1px solid rgba(148, 163, 184, 0.12);
    border-radius: 22px;
    padding: 0.65rem 0.45rem 0.8rem 0.45rem;
    margin-top: 0.35rem;
}

div[data-testid="stSidebarNav"] header {
    color: #cbd5e1;
    font-size: 0.9rem;
    font-weight: 700;
    letter-spacing: -0.01em;
    margin: 0.8rem 0 0.35rem 0;
}

div[data-testid="stSidebarNav"] header:first-of-type {
    margin-top: 0.1rem;
}

a[data-testid="stSidebarNavLink"] {
    min-height: 46px;
    padding: 0.72rem 0.85rem;
    border: 1px solid transparent;
    border-radius: 14px;
    transition: background-color 160ms ease, border-color 160ms ease, transform 160ms ease;
}

a[data-testid="stSidebarNavLink"]:hover {
    background: rgba(255, 255, 255, 0.05);
    border-color: rgba(148, 163, 184, 0.14);
    transform: translateX(2px);
}

a[data-testid="stSidebarNavLink"][aria-current="page"] {
    background: linear-gradient(180deg, rgba(71, 85, 105, 0.88) 0%, rgba(55, 65, 81, 0.92) 100%);
    border-color: rgba(148, 163, 184, 0.22);
    box-shadow:
        inset 0 1px 0 rgba(255, 255, 255, 0.05),
        0 8px 24px rgba(2, 6, 23, 0.18);
}

a[data-testid="stSidebarNavLink"] span {
    font-size: 0.98rem;
}
</style>
""",
    unsafe_allow_html=True,
)

pages = {
    "": [
        st.Page(
            "Horizon_2040.py",
            title="🏠 HORIZON 2040",
            default=True,
        ),
    ],
    "🌍 Contraintes 2040": [
        st.Page(
            "pages/1_Climat.py",
            title="Climat",
            url_path="climat",
        ),
        st.Page(
            "pages/2_Transition_démographique.py",
            title="Transition démographique",
            url_path="transition-demographique",
        ),
    ],
    "🧭 Conditions de vie": [
        st.Page(
            "pages/4_Emplois_chomage.py",
            title="Emploi",
            url_path="emploi",
        ),
        st.Page(
            "pages/5_Revenu.py",
            title="Revenu",
            url_path="revenu",
        ),
        st.Page(
            "pages/6_Santé.py",
            title="Santé",
            url_path="sante",
        ),
        st.Page(
            "pages/8_Education.py",
            title="Éducation",
            url_path="education",
        ),
        st.Page(
            "pages/10_Internet.py",
            title="Fibre",
            url_path="fibre",
        ),
        st.Page(
            "pages/7_Criminalite.py",
            title="Sécurité",
            url_path="securite",
        ),
        st.Page(
            "pages/3_Immobilier.py",
            title="Immobilier",
            url_path="immobilier",
        ),
    ],
}

current_page = st.navigation(pages, position="sidebar", expanded=True)
current_page.run()
