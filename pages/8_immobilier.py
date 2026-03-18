import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.excel_helpers import charger_csv, charger_geojson

st.title("Prix de l'immobilier par département")

geojson_departements = charger_geojson("pages/tables/departements.geojson")

df = charger_csv("pages/tables/Real_Estate_Prices.csv", sep=";")
df["num_dep"] = df["num_dep"].astype(str).str.zfill(2)

colonnes_num = ["Price2025", "Price2040", "Growth", "Coefficient"]
for colonne in colonnes_num:
    df[colonne] = pd.to_numeric(df[colonne], errors="coerce")

df["Price2025"] = df["Price2025"].round(0)
df["Price2040"] = df["Price2040"].round(0)
df["Growth (%)"] = df["Growth"] * 100
df["Coefficient (%)"] = df["Coefficient"] * 100

indicateurs = {
    "Prix 2025": "Price2025",
    "Prix 2040": "Price2040",
    "Croissance 2025-2040": "Growth (%)",
    "Coefficient": "Coefficient (%)",
}
indicateur = st.selectbox("Indicateur affiché sur la carte", list(indicateurs.keys()))
colonne_carte = indicateurs[indicateur]

col1, col2, col3 = st.columns(3)
col1.metric("Départements couverts", f"{df['dep_name'].nunique()}")
col2.metric("Prix moyen 2025", f"{df['Price2025'].mean():,.0f} €/m²".replace(",", " "))
col3.metric("Prix moyen 2040", f"{df['Price2040'].mean():,.0f} €/m²".replace(",", " "))

fig_carte = px.choropleth(
    df,
    geojson=geojson_departements,
    locations="dep_name",
    featureidkey="properties.nom",
    color=colonne_carte,
    hover_name="dep_name",
    hover_data={
        "region_name": True,
        "Price2025": ":,.0f",
        "Price2040": ":,.0f",
        "Growth (%)": ":.1f",
        "Coefficient (%)": ":.1f",
    },
    color_continuous_scale="YlOrRd",
    labels={
        "Price2025": "Prix 2025 (€/m²)",
        "Price2040": "Prix 2040 (€/m²)",
        "Growth (%)": "Croissance (%)",
        "Coefficient (%)": "Coefficient (%)",
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

st.subheader("Classements immobiliers")
st.caption("Vue directe sur les départements les plus chers et les mieux notés.")

gauche, droite = st.columns(2, gap="large")

top_prix = (
    df.dropna(subset=["dep_name", "Price2025"])
    .sort_values("Price2025", ascending=False)
    .head(12)
)
fig_prix = px.bar(
    top_prix,
    x="Price2025",
    y="dep_name",
    orientation="h",
    title="Départements les plus chers",
    labels={"dep_name": "Département", "Price2025": "Prix 2025 (€/m²)"},
)
fig_prix.update_traces(
    marker_color="#f97316",
    hovertemplate="<b>%{y}</b><br>Prix 2025: %{x:,.0f} €/m²<extra></extra>",
)
fig_prix.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    height=560,
    showlegend=False,
    bargap=0.18,
    xaxis={"showgrid": True, "gridcolor": "rgba(255,255,255,0.08)"},
    margin={"l": 0, "r": 0, "t": 50, "b": 0},
    yaxis={"title": None, "tickfont": {"size": 13}},
)
fig_prix.update_yaxes(categoryorder="total ascending", automargin=True)
fig_prix.update_xaxes(automargin=True)
gauche.plotly_chart(fig_prix, use_container_width=True)

top_coef = df.sort_values("Coefficient (%)", ascending=False).head(15)
fig_coef = px.bar(
    top_coef.head(12),
    x="Coefficient (%)",
    y="dep_name",
    orientation="h",
    title="Départements les mieux notés",
    labels={"dep_name": "Département", "Coefficient (%)": "Coefficient (%)"},
    text="Coefficient (%)",
)
fig_coef.update_traces(
    marker_color="#22c55e",
    texttemplate="%{text:.0f}",
    textposition="outside",
    cliponaxis=False,
    hovertemplate="<b>%{y}</b><br>Coefficient: %{x:.1f}%<extra></extra>",
)
fig_coef.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    height=560,
    bargap=0.18,
    margin={"l": 0, "r": 0, "t": 50, "b": 0},
    yaxis={"title": None, "tickfont": {"size": 13}},
    showlegend=False,
)
fig_coef.update_yaxes(categoryorder="total ascending", automargin=True)
fig_coef.update_xaxes(automargin=True)
droite.plotly_chart(fig_coef, use_container_width=True)

fig_scatter = px.scatter(
    df,
    x="Price2025",
    y="Price2040",
    size="Coefficient (%)",
    color="Growth (%)",
    hover_name="dep_name",
    title="Projection 2040 du prix au m²",
    labels={
        "Price2025": "Prix 2025 (€/m²)",
        "Price2040": "Prix 2040 (€/m²)",
        "Growth (%)": "Croissance (%)",
    },
    color_continuous_scale="RdYlGn",
)
fig_scatter.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
)
st.plotly_chart(fig_scatter, use_container_width=True)

with st.expander("Voir les données"):
    st.dataframe(
        df[
            [
                "num_dep",
                "dep_name",
                "region_name",
                "Price2025",
                "Price2040",
                "Growth (%)",
                "Coefficient (%)",
            ]
        ]
        .sort_values("Coefficient (%)", ascending=False)
        .style.format(
            {
                "Price2025": "{:,.0f}",
                "Price2040": "{:,.0f}",
                "Growth (%)": "{:.1f}",
                "Coefficient (%)": "{:.1f}",
            }
        ),
        use_container_width=True,
    )
