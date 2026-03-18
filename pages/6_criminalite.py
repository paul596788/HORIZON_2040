import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.excel_helpers import charger_csv, charger_geojson

st.title("Criminalité projetée par département")

df = charger_csv("pages/tables/CrimebyDept_2040.csv")
geojson_departements = charger_geojson("pages/tables/departements.geojson")

df["num_dep"] = df["num_dep"].astype(str).str.zfill(2)
df["nombre"] = pd.to_numeric(df["nombre"], errors="coerce")
df["Coefficient"] = pd.to_numeric(df["Coefficient"], errors="coerce")

indicateurs = {
    "Nombre de crimes projetés": "nombre",
    "Coefficient de sécurité": "Coefficient",
}
indicateur = st.selectbox("Indicateur affiché sur la carte", list(indicateurs.keys()))
colonne_carte = indicateurs[indicateur]

col1, col2, col3 = st.columns(3)
col1.metric("Départements couverts", f"{df['dep_name'].nunique()}")
col2.metric("Crimes projetés moyens", f"{df['nombre'].mean():,.0f}".replace(",", " "))
col3.metric(
    "Département le plus sûr",
    df.sort_values("Coefficient", ascending=False).iloc[0]["dep_name"],
)

fig_carte = px.choropleth(
    df,
    geojson=geojson_departements,
    locations="dep_name",
    featureidkey="properties.nom",
    color=colonne_carte,
    hover_name="dep_name",
    hover_data={
        "num_dep": True,
        "nombre": ":,",
        "Coefficient": ":.2f",
    },
    color_continuous_scale="YlOrRd" if colonne_carte == "nombre" else "YlGn",
    labels={"nombre": "Crimes projetés", "Coefficient": "Coefficient"},
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
    color="Coefficient",
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

top_safe = df.sort_values("Coefficient", ascending=False).head(15)
fig_safe = px.bar(
    top_safe,
    x="Coefficient",
    y="dep_name",
    orientation="h",
    color="Coefficient",
    title="Départements les mieux notés par le coefficient",
    labels={"dep_name": "Département"},
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
    df.sort_values("Coefficient"),
    x="Coefficient",
    y="nombre",
    hover_name="dep_name",
    text="num_dep",
    title="Relation entre coefficient et volume de crimes",
    labels={"nombre": "Crimes projetés"},
    color="Coefficient",
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
        df.sort_values("Coefficient", ascending=False).style.format(
            {"nombre": "{:,.0f}", "Coefficient": "{:.2f}"}
        ),
        use_container_width=True,
    )
