import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path


st.set_page_config(page_title="Où vivre en 2040 ?", layout="wide")

st.title("Dashboard interactif")

# emplois et chomage
chomage_2000_2025_dep = "tables/emplois et chomage/Demandeurs_emploi_taux_chomage_2000_2025.xlsx"
emplois_par_ststus_secteur = "tables/emplois et chomage/ECRT2024_F1.xlsx"
emplois_par_region = "tables/emplois et chomage/emplois en 2020 par region.xlsx"

# etudiants
etudes_sup_dep_reg_2001_2023 = "tables/etudiants/fr-esr-atlas_regional-effectifs-d-etudiants-inscrits_agregeables.xlsx"

# revenu
disparité_de_revenus = "tables/revenu/base-cc-filosofi-2021-geo2025.xlsx"
déclaratif_par_commune = "tables/revenu/FILO2021_DEC_COM.xlsx"
dispo_par_commune = "tables/revenu/FILO2021_DISP_COM.xlsx"

# santé
données_accès_hopitaux = "tables/Santé/analyse_acces_hopital_2010.xlsx"
couverture_medicale_2024 = "tables/Santé/santé data.xlsx"


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
