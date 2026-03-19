import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.excel_helpers import charger_csv, charger_geojson

st.title("Criminalité projetée par département")

df = charger_csv("pages/tables/CrimebyDept_2040.csv")
geojson_departements = charger_geojson("pages/tables/departements.geojson")

df.columns = [str(col).strip() for col in df.columns]
if "Coefficient" in df.columns and "coefficient" not in df.columns:
    df = df.rename(columns={"Coefficient": "coefficient"})
if "taux_pour_mille_2040" not in df.columns:
    df["taux_pour_mille_2040"] = pd.NA

df["num_dep"] = df["num_dep"].astype(str).str.zfill(2)
df["nombre"] = pd.to_numeric(df["nombre"], errors="coerce")
df["coefficient"] = pd.to_numeric(df["coefficient"], errors="coerce")
df["taux_pour_mille_2040"] = pd.to_numeric(df["taux_pour_mille_2040"], errors="coerce")
df["Coefficient favorable"] = (1 - df["coefficient"]) * 100
df["Crimes pour 1000 habitants"] = df["taux_pour_mille_2040"] * 1000

has_rate = df["Crimes pour 1000 habitants"].notna().any()
indicateurs = {
    "Nombre de crimes projetés": "nombre",
    "Score sécurité": "Coefficient favorable",
}
if has_rate:
    indicateurs["Crimes pour 1000 habitants"] = "Crimes pour 1000 habitants"

indicateur = st.selectbox("Indicateur affiché sur la carte", list(indicateurs.keys()))
colonne_carte = indicateurs[indicateur]

col1, col2, col3 = st.columns(3)
col1.metric("Départements couverts", f"{df['dep_name'].nunique()}")
if has_rate:
    col2.metric("Crimes moyens pour 1000 hab.", f"{df['Crimes pour 1000 habitants'].mean():.1f}")
else:
    col2.metric("Crimes moyens pour 1000 hab.", "N/A")
col3.metric(
    "Département le plus sûr",
    df.sort_values("Coefficient favorable", ascending=False).iloc[0]["dep_name"],
)

hover_data = {
    "num_dep": True,
    "nombre": ":,",
    "Coefficient favorable": ":.1f",
}
if has_rate:
    hover_data["Crimes pour 1000 habitants"] = ":.1f"

fig_carte = px.choropleth(
    df,
    geojson=geojson_departements,
    locations="dep_name",
    featureidkey="properties.nom",
    color=colonne_carte,
    hover_name="dep_name",
    hover_data=hover_data,
    color_continuous_scale="YlOrRd" if colonne_carte != "Coefficient favorable" else "YlGn",
    labels={
        "nombre": "Crimes projetés",
        "Crimes pour 1000 habitants": "Crimes pour 1000 hab.",
        "Coefficient favorable": "Score sécurité",
    },
)
fig_carte.update_geos(fitbounds="locations", visible=False, projection={"type": "mercator"})
fig_carte.update_layout(
    template="plotly_dark",
    height=700,
    margin={"l": 0, "r": 0, "t": 10, "b": 0},
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
)
st.plotly_chart(fig_carte, use_container_width=True)

gauche, droite = st.columns(2)

top_crimes = df.sort_values("nombre", ascending=False).head(15)
fig_top = px.bar(
    top_crimes,
    x="nombre",
    y="dep_name",
    orientation="h",
    color="Crimes pour 1000 habitants" if has_rate else "Coefficient favorable",
    title="Départements avec le plus de crimes projetés",
    labels={"dep_name": "Département", "nombre": "Crimes projetés"},
    color_continuous_scale="YlOrRd_r",
)
fig_top.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
)
fig_top.update_yaxes(categoryorder="total ascending")
gauche.plotly_chart(fig_top, use_container_width=True)

top_safe = df.sort_values("Coefficient favorable", ascending=False).head(15)
fig_safe = px.bar(
    top_safe,
    x="Coefficient favorable",
    y="dep_name",
    orientation="h",
    color="Coefficient favorable",
    title="Départements les plus sûrs selon le score favorable",
    labels={"dep_name": "Département", "Coefficient favorable": "Score sécurité"},
    color_continuous_scale="YlGn",
)
fig_safe.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
)
fig_safe.update_yaxes(categoryorder="total ascending")
droite.plotly_chart(fig_safe, use_container_width=True)

fig_scatter = px.scatter(
    df.sort_values("Coefficient favorable"),
    x="Crimes pour 1000 habitants" if has_rate else "Coefficient favorable",
    y="nombre",
    hover_name="dep_name",
    text="num_dep",
    title="Volume de crimes et intensité rapportée à la population",
    labels={"nombre": "Crimes projetés"},
    color="Coefficient favorable",
    color_continuous_scale="Viridis",
)
fig_scatter.update_traces(textposition="top center")
fig_scatter.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
)
st.plotly_chart(fig_scatter, use_container_width=True)

with st.expander("Voir les données"):
    st.dataframe(
        df.sort_values("Coefficient favorable", ascending=False).style.format(
            {
                "nombre": "{:,.0f}",
                "Crimes pour 1000 habitants": "{:.1f}",
                "Coefficient favorable": "{:.1f}",
            }
        ),
        use_container_width=True,
    )
