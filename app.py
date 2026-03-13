import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path


st.set_page_config(page_title="Où vivre en 2040 ?", layout="wide")

st.title("Évolution du chômage par département")

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


# Jeu de données chomage
chomage_df = pd.read_excel(chomage_2000_2025_dep)

chomage_df.columns = chomage_df.columns.str.strip()

# Colonnes des taux de chômage
taux_cols = [col for col in chomage_df.columns if col.startswith("Taux de chomage")]

if not taux_cols:
    st.error("Aucune colonne 'Taux de chomage ...' trouvée dans le fichier Excel.")
    st.stop()

    # Passage du format large au format long
df_long = chomage_df.melt(
    id_vars=["Département"],
    value_vars=taux_cols,
    var_name="Année",
    value_name="Taux de chômage"
)

# Extraire l'année depuis 'Taux de chomage 2000'
df_long["Année"] = df_long["Année"].str.extract(r"(\d{4})").astype(int)

# Sécurise le type numérique
df_long["Taux de chômage"] = (
    df_long["Taux de chômage"]
    .astype(str)
    .str.replace(",", ".", regex=False)
)
df_long["Taux de chômage"] = pd.to_numeric(df_long["Taux de chômage"], errors="coerce")

liste_departements = sorted(df_long["Département"].dropna().astype(str).unique())

departements_selectionnes = st.multiselect(
    "Choisis un ou plusieurs départements",
    options=liste_departements,
    default=liste_departements[:1]
)
if not departements_selectionnes:
    st.warning("Sélectionne au moins un département.")
    st.stop()

df_filtre = df_long[df_long["Département"].isin(departements_selectionnes)]

# Graphique
fig = px.line(
    df_filtre,
    x="Année",
    y="Taux de chômage",
    color="Département",
    markers=True,
    title="Évolution du taux de chômage"
)

st.plotly_chart(fig, use_container_width=True)

# Tableau en dessous
st.subheader("Données utilisées")
st.dataframe(df_filtre, use_container_width=True)
