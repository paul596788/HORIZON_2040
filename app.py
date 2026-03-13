import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Mon dashboard", layout="wide")

st.title("Dashboard interactif en Python")

# Jeu de données simple
df = pd.DataFrame({
    "mois": ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin"],
    "ventes": [120, 180, 150, 220, 260, 300],
    "couts": [80, 110, 105, 140, 170, 210],
})

metrique = st.selectbox("Choisis une métrique", ["ventes", "couts"])

fig = px.bar(
    df,
    x="mois",
    y=metrique,
    title=f"Évolution des {metrique}"
)

st.plotly_chart(fig, use_container_width=True)

st.dataframe(df)
