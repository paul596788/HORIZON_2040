import streamlit as st
import pandas as pd
import plotly.express as px
from utils.excel_helpers import (
    charger_excel,
    get_global_department_selection,
    nettoyer_colonnes,
    render_global_department_selector,
)

st.title("Évolution du chômage par département")

df = charger_excel("pages/tables/emplois_et_chomage/Demandeurs_emploi_taux_chomage_2000_2025.xlsx")
df = nettoyer_colonnes(df)

taux_cols = [col for col in df.columns if "Taux de chomage" in col or "Taux de chômage" in col]

df_long = df.melt(
    id_vars=["Département"],
    value_vars=taux_cols,
    var_name="Année",
    value_name="Taux de chômage"
)

df_long["Année"] = df_long["Année"].astype(str).str.extract(r"(\d{4})")
df_long = df_long.dropna(subset=["Année"])
df_long["Année"] = df_long["Année"].astype(int)

df_long["Taux de chômage"] = (
    df_long["Taux de chômage"]
    .astype(str)
    .str.replace(",", ".", regex=False)
)
df_long["Taux de chômage"] = pd.to_numeric(df_long["Taux de chômage"], errors="coerce")

departements = sorted(df_long["Département"].dropna().unique())

render_global_department_selector(
    caption="La sélection est partagée entre les pages. Sans sélection, la page affiche un département repère par défaut."
)
selection = get_global_department_selection(departements) or departements[:1]

df_filtre = df_long[df_long["Département"].isin(selection)]

fig = px.line(
    df_filtre,
    x="Année",
    y="Taux de chômage",
    color="Département",
    markers=True
)

st.plotly_chart(fig, use_container_width=True)
