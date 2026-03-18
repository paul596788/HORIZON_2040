import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.excel_helpers import charger_csv, charger_geojson

st.title("Éducation et dynamique étudiante")

geojson_departements = charger_geojson("pages/tables/departements.geojson")
code_to_name = {
    feature["properties"]["code"]: feature["properties"]["nom"]
    for feature in geojson_departements["features"]
}

df = charger_csv("pages/tables/Education.csv")
df["num_dep"] = df["num_dep"].astype(str).str.zfill(2)
df["Département"] = df["num_dep"].map(code_to_name)

colonnes_num = [
    "nb_stud_total",
    "POP_2024",
    "POP_2040",
    "nb_stud_total_2040",
    "nb_student_change_pct",
    "pop_change_pct",
    "Student_Pop_Ratio",
    "coefficient",
]
for colonne in colonnes_num:
    df[colonne] = pd.to_numeric(df[colonne], errors="coerce")

df["Taux étudiants 2024 (%)"] = df["nb_stud_total"] / df["POP_2024"] * 100
df["Taux étudiants 2040 (%)"] = df["nb_stud_total_2040"] / df["POP_2040"] * 100
df["Évolution étudiants (%)"] = df["nb_student_change_pct"] * 100
df["Évolution population (%)"] = df["pop_change_pct"] * 100
df["Coefficient (%)"] = df["coefficient"] * 100

indicateurs = {
    "Coefficient": "Coefficient (%)",
    "Étudiants 2024": "nb_stud_total",
    "Étudiants 2040": "nb_stud_total_2040",
    "Taux étudiants / population 2024": "Taux étudiants 2024 (%)",
}
indicateur = st.selectbox("Indicateur affiché sur la carte", list(indicateurs.keys()))
colonne_carte = indicateurs[indicateur]

col1, col2, col3 = st.columns(3)
col1.metric("Départements couverts", f"{df['Département'].nunique()}")
col2.metric("Étudiants 2024 moyens", f"{df['nb_stud_total'].mean():,.0f}".replace(",", " "))
col3.metric(
    "Meilleur coefficient",
    df.sort_values("Coefficient (%)", ascending=False).iloc[0]["Département"],
)

fig_carte = px.choropleth(
    df.dropna(subset=["Département"]),
    geojson=geojson_departements,
    locations="Département",
    featureidkey="properties.nom",
    color=colonne_carte,
    hover_name="Département",
    hover_data={
        "nb_stud_total": ":,.0f",
        "POP_2024": ":,.0f",
        "nb_stud_total_2040": ":,.0f",
        "Taux étudiants 2024 (%)": ":.2f",
        "Coefficient (%)": ":.1f",
    },
    color_continuous_scale="YlGnBu",
    labels={
        "nb_stud_total": "Étudiants 2024",
        "nb_stud_total_2040": "Étudiants 2040",
        "POP_2024": "Population 2024",
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

gauche, droite = st.columns(2)

top_coef = df.sort_values("Coefficient (%)", ascending=False).head(15)
fig_coef = px.bar(
    top_coef,
    x="Coefficient (%)",
    y="Département",
    orientation="h",
    color="Coefficient (%)",
    title="Top 15 des départements selon le coefficient éducation",
    color_continuous_scale="YlGn",
)
fig_coef.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
)
fig_coef.update_yaxes(categoryorder="total ascending")
gauche.plotly_chart(fig_coef, use_container_width=True)

top_ratio = df.sort_values("Taux étudiants 2024 (%)", ascending=False).head(15)
fig_ratio = px.bar(
    top_ratio,
    x="Taux étudiants 2024 (%)",
    y="Département",
    orientation="h",
    color="Taux étudiants 2024 (%)",
    title="Part des étudiants dans la population en 2024",
    color_continuous_scale="Tealgrn",
)
fig_ratio.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
)
fig_ratio.update_yaxes(categoryorder="total ascending")
droite.plotly_chart(fig_ratio, use_container_width=True)

fig_scatter = px.scatter(
    df,
    x="POP_2024",
    y="nb_stud_total",
    size="nb_stud_total_2040",
    color="Coefficient (%)",
    hover_name="Département",
    title="Étudiants 2024, population départementale et projection 2040",
    labels={
        "POP_2024": "Population 2024",
        "nb_stud_total": "Étudiants 2024",
        "nb_stud_total_2040": "Étudiants 2040",
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
        df[
            [
                "num_dep",
                "Département",
                "nb_stud_total",
                "POP_2024",
                "nb_stud_total_2040",
                "Taux étudiants 2024 (%)",
                "Coefficient (%)",
            ]
        ]
        .sort_values("Coefficient (%)", ascending=False)
        .style.format(
            {
                "nb_stud_total": "{:,.0f}",
                "POP_2024": "{:,.0f}",
                "nb_stud_total_2040": "{:,.0f}",
                "Taux étudiants 2024 (%)": "{:.2f}",
                "Coefficient (%)": "{:.1f}",
            }
        ),
        use_container_width=True,
    )
