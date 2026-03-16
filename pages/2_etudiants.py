import pandas as pd
import plotly.express as px
import streamlit as st

from utils.excel_helpers import charger_excel, nettoyer_colonnes


st.title("Effectifs étudiants")

df = charger_excel(
    "pages/tables/etudiants/fr-esr-atlas_regional-effectifs-d-etudiants-inscrits_agregeables.xlsx"
)
df = nettoyer_colonnes(df)
df["Nombre total d’étudiants inscrits"] = pd.to_numeric(
    df["Nombre total d’étudiants inscrits"], errors="coerce"
)
df["Année civile concernée"] = pd.to_numeric(df["Année civile concernée"], errors="coerce")

departements = sorted(df["Département"].dropna().unique())
departement_selection = st.multiselect(
    "Départements à afficher",
    departements,
    default=departements[:1],
)

df_filtre = df[df["Département"].isin(departement_selection)] if departement_selection else df.copy()

serie_departements = (
    df_filtre.groupby(["Année civile concernée", "Département"], as_index=False)[
        "Nombre total d’étudiants inscrits"
    ]
    .sum()
    .sort_values("Année civile concernée")
)

col1, col2, col3 = st.columns(3)
col1.metric("Départements affichés", f"{df_filtre['Département'].nunique()}")
col2.metric("Régions couvertes", f"{df_filtre['Région'].nunique()}")
col3.metric(
    "Étudiants 2024",
    f"{int(serie_departements[serie_departements['Année civile concernée'] == 2024]['Nombre total d’étudiants inscrits'].sum()):,}".replace(",", " "),
)

fig_evolution = px.line(
    serie_departements,
    x="Année civile concernée",
    y="Nombre total d’étudiants inscrits",
    color="Département",
    markers=True,
    labels={
        "Année civile concernée": "Année",
        "Nombre total d’étudiants inscrits": "Étudiants inscrits",
    },
)
st.plotly_chart(fig_evolution, use_container_width=True)

annee_reference = int(df["Année civile concernée"].dropna().max())
departements_annee = (
    df_filtre[df_filtre["Année civile concernée"] == annee_reference]
    .groupby("Département", as_index=False)["Nombre total d’étudiants inscrits"]
    .sum()
    .sort_values("Nombre total d’étudiants inscrits", ascending=False)
    .head(15)
)

fig_departements = px.bar(
    departements_annee,
    x="Nombre total d’étudiants inscrits",
    y="Département",
    orientation="h",
    title=f"Top 15 des départements en {annee_reference}",
    labels={"Nombre total d’étudiants inscrits": "Étudiants inscrits"},
)
fig_departements.update_layout(yaxis={"categoryorder": "total ascending"})
st.plotly_chart(fig_departements, use_container_width=True)

communes_departement = (
    df_filtre[df_filtre["Année civile concernée"] == annee_reference]
    .groupby(["Département", "Commune"], as_index=False)["Nombre total d’étudiants inscrits"]
    .sum()
)

departement_focus = st.selectbox(
    f"Zoom sur les communes en {annee_reference}",
    sorted(communes_departement["Département"].dropna().unique()),
)

top_communes = (
    communes_departement[communes_departement["Département"] == departement_focus]
    .sort_values("Nombre total d’étudiants inscrits", ascending=False)
    .head(15)
)

fig_communes = px.bar(
    top_communes,
    x="Commune",
    y="Nombre total d’étudiants inscrits",
    color="Nombre total d’étudiants inscrits",
    title=f"Communes étudiantes les plus importantes dans {departement_focus}",
    labels={"Nombre total d’étudiants inscrits": "Étudiants inscrits"},
)
fig_communes.update_xaxes(tickangle=-35)
st.plotly_chart(fig_communes, use_container_width=True)

with st.expander("Aperçu des données filtrées"):
    st.dataframe(
        df_filtre[
            [
                "Année universitaire",
                "Commune",
                "Département",
                "Région",
                "Nombre total d’étudiants inscrits",
            ]
        ].head(200),
        use_container_width=True,
    )
