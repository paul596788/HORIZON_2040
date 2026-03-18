import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.excel_helpers import charger_csv, charger_geojson

st.title("Déploiement de la fibre en France")

df = charger_csv("pages/tables/Internet.csv")
geojson_departements = charger_geojson("pages/tables/departements.geojson")
corrections_noms = {
    "Côtes d'Armor": "Côtes-d'Armor",
    "Seine-St-Denis": "Seine-Saint-Denis",
    "Val-D'Oise": "Val-d'Oise",
}

df["Dep_num"] = df["Dep_num"].astype(str).str.zfill(2)
df["Dep_name"] = df["Dep_name"].replace(corrections_noms)
df["Fibre (%)"] = df["Fibre"] * 100
df["Coefficient (%)"] = df["Coefficient"] * 100

indicateurs_carte = {
    "Taux de fibre": "Fibre (%)",
    "Coefficient": "Coefficient (%)",
    "Nombre de locaux": "Nombre de locaux",
}

indicateur = st.selectbox("Indicateur affiché sur la carte", list(indicateurs_carte.keys()))
colonne_carte = indicateurs_carte[indicateur]

col1, col2, col3 = st.columns(3)
col1.metric("Départements couverts", f"{df['Dep_name'].nunique()}")
col2.metric("Taux moyen de fibre", f"{df['Fibre (%)'].mean():.1f}%")
col3.metric("Département le mieux couvert", df.sort_values("Fibre (%)", ascending=False).iloc[0]["Dep_name"])

fig_carte = px.choropleth(
    df,
    geojson=geojson_departements,
    locations="Dep_name",
    featureidkey="properties.nom",
    color=colonne_carte,
    hover_name="Dep_name",
    hover_data={
        "Dep_num": True,
        "Nombre de locaux": ":,",
        "Fibre (%)": ":.1f",
        "Coefficient (%)": ":.1f",
    },
    color_continuous_scale="YlGnBu",
    labels={colonne_carte: indicateur},
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

col_gauche, col_droite = st.columns(2)

top_fibre = df.sort_values("Fibre (%)", ascending=False).head(15)
fig_top = px.bar(
    top_fibre,
    x="Fibre (%)",
    y="Dep_name",
    orientation="h",
    color="Fibre (%)",
    title="Top 15 des départements les mieux couverts en fibre",
    labels={"Dep_name": "Département"},
    color_continuous_scale="YlGn",
)
fig_top.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
)
fig_top.update_yaxes(categoryorder="total ascending")
col_gauche.plotly_chart(fig_top, use_container_width=True)

bottom_fibre = df.sort_values("Fibre (%)", ascending=True).head(15)
fig_bottom = px.bar(
    bottom_fibre,
    x="Fibre (%)",
    y="Dep_name",
    orientation="h",
    color="Fibre (%)",
    title="15 départements les moins couverts en fibre",
    labels={"Dep_name": "Département"},
    color_continuous_scale="OrRd",
)
fig_bottom.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
)
fig_bottom.update_yaxes(categoryorder="total ascending")
col_droite.plotly_chart(fig_bottom, use_container_width=True)

fig_scatter = px.scatter(
    df,
    x="Nombre de locaux",
    y="Fibre (%)",
    size="Coefficient (%)",
    color="Coefficient (%)",
    hover_name="Dep_name",
    title="Couverture fibre selon le nombre de locaux",
    labels={
        "Fibre (%)": "Fibre (%)",
        "Nombre de locaux": "Nombre de locaux",
        "Coefficient (%)": "Coefficient (%)",
    },
    color_continuous_scale="Viridis",
)
fig_scatter.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
)
st.plotly_chart(fig_scatter, use_container_width=True)

with st.expander("Voir les données"):
    st.dataframe(
        df[["Dep_num", "Dep_name", "Nombre de locaux", "Fibre (%)", "Coefficient (%)"]]
        .sort_values("Fibre (%)", ascending=False)
        .style.format(
            {
                "Nombre de locaux": "{:,.0f}",
                "Fibre (%)": "{:.1f}",
                "Coefficient (%)": "{:.1f}",
            }
        ),
        use_container_width=True,
    )
