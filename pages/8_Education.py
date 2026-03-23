import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.excel_helpers import (
    ajouter_surlignage_departements,
    charger_csv,
    charger_geojson,
    get_global_department_selection,
    render_global_department_selector,
    styliser_carte_departements,
)
from utils.ui_theme import apply_horizon_theme

apply_horizon_theme()
st.title("Éducation et dynamique étudiante")
render_global_department_selector(
    caption="La sélection est partagée entre les pages. Les départements choisis sont surlignés sur la carte et filtrent les graphiques."
)

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

df["Taux élèves 2024 (%)"] = df["nb_stud_total"] / df["POP_2024"] * 100
df["Taux élèves 2040 (%)"] = df["nb_stud_total_2040"] / df["POP_2040"] * 100
df["Évolution élèves (%)"] = df["nb_student_change_pct"] * 100
df["Évolution population (%)"] = df["pop_change_pct"] * 100
df["Coefficient (%)"] = df["coefficient"] * 100
departements_selectionnes = get_global_department_selection(df["Département"].dropna().unique())
df_scope = df[df["Département"].isin(departements_selectionnes)].copy() if departements_selectionnes else df.copy()

indicateurs = {
    "Coefficient": "Coefficient (%)",
    "Élèves 2024": "nb_stud_total",
    "Élèves 2040": "nb_stud_total_2040",
    "Taux élèves / population 2024": "Taux élèves 2024 (%)",
}
indicateur = st.selectbox("Indicateur affiché sur la carte", list(indicateurs.keys()))
colonne_carte = indicateurs[indicateur]
leader_education = df_scope.sort_values("Coefficient (%)", ascending=False).iloc[0]
education_scale = [
    (0.0, "#f8fafc"),
    (0.22, "#d7f1ea"),
    (0.48, "#8ad7c4"),
    (0.74, "#2ea39b"),
    (1.0, "#155e75"),
]

col1, col2, col3 = st.columns(3)
col1.metric("Élèves 2024 moyens", f"{df_scope['nb_stud_total'].mean():,.0f}".replace(",", " "))
col2.metric("Meilleur département", leader_education["Département"])
col3.metric("Score du leader", f"{leader_education['Coefficient (%)']:.1f}%")

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
        "Taux élèves 2024 (%)": ":.2f",
        "Coefficient (%)": ":.1f",
    },
    labels={
        "nb_stud_total": "Élèves 2024",
        "nb_stud_total_2040": "Élèves 2040",
        "POP_2024": "Population 2024",
        "Coefficient (%)": "Coefficient (%)",
    },
    color_continuous_scale=education_scale,
)
fig_carte = styliser_carte_departements(
    fig_carte,
    indicateur,
    height=700,
    tickformat=",.0f" if colonne_carte in {"nb_stud_total", "nb_stud_total_2040"} else ".1f",
)
fig_carte = ajouter_surlignage_departements(
    fig_carte,
    geojson_departements,
    departements_selectionnes,
    "properties.nom",
)
st.plotly_chart(fig_carte, use_container_width=True)

gauche, droite = st.columns(2)

top_coef = df_scope.sort_values("Coefficient (%)", ascending=False).head(15)
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

top_ratio = df_scope.sort_values("Taux élèves 2024 (%)", ascending=False).head(15)
fig_ratio = px.bar(
    top_ratio,
    x="Taux élèves 2024 (%)",
    y="Département",
    orientation="h",
    color="Taux élèves 2024 (%)",
    title="Part des élèves dans la population en 2024",
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
    df_scope,
    x="POP_2024",
    y="nb_stud_total",
    size="nb_stud_total_2040",
    color="Coefficient (%)",
    hover_name="Département",
    title="Élèves 2024, population départementale et projection 2040",
    labels={
        "POP_2024": "Population 2024",
        "nb_stud_total": "Élèves 2024",
        "nb_stud_total_2040": "Élèves 2040",
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
        df_scope[
            [
                "num_dep",
                "Département",
                "nb_stud_total",
                "POP_2024",
                "nb_stud_total_2040",
                "Taux élèves 2024 (%)",
                "Coefficient (%)",
            ]
        ]
        .sort_values("Coefficient (%)", ascending=False)
        .style.format(
            {
                "nb_stud_total": "{:,.0f}",
                "POP_2024": "{:,.0f}",
                "nb_stud_total_2040": "{:,.0f}",
                "Taux élèves 2024 (%)": "{:.2f}",
                "Coefficient (%)": "{:.1f}",
            }
        ),
        use_container_width=True,
    )
