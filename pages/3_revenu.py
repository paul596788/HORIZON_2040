import pandas as pd
import plotly.express as px
import streamlit as st

from utils.excel_helpers import charger_excel, nettoyer_colonnes


st.title("Niveaux de vie et pauvreté")

chemin_fichier = "pages/tables/revenu/base-cc-filosofi-2021-geo2025.xlsx"
df_reg = nettoyer_colonnes(charger_excel(chemin_fichier, sheet_name="REG"))
df_dep = nettoyer_colonnes(charger_excel(chemin_fichier, sheet_name="DEP"))

mesures = [
    "Niveau de vie médian (en euros)",
    "Taux de pauvreté (en %) au seuil de 60 % de la médiane du niveau de vie",
    "Part des ménages imposés (en %)",
    "Rapport interdécile (D9/D1) du niveau de vie",
]

for colonne in mesures:
    df_reg[colonne] = pd.to_numeric(df_reg[colonne], errors="coerce")
    df_dep[colonne] = pd.to_numeric(df_dep[colonne], errors="coerce")

col1, col2 = st.columns([1, 1])
niveau_geo = col1.radio("Niveau géographique", ["Régions", "Départements"], horizontal=True)
indicateur = col2.selectbox("Indicateur", mesures)

df_actuel = df_reg if niveau_geo == "Régions" else df_dep
nom_geo = "Géographie"
top_n = 15 if niveau_geo == "Régions" else 20

resume = df_actuel[indicateur].dropna()
met1, met2, met3 = st.columns(3)
met1.metric("Moyenne", f"{resume.mean():.1f}")
met2.metric("Médiane", f"{resume.median():.1f}")
met3.metric("Maximum", f"{resume.max():.1f}")

classement = df_actuel[[nom_geo, indicateur]].dropna().sort_values(indicateur, ascending=False)

fig_classement = px.bar(
    classement.head(top_n),
    x=indicateur,
    y=nom_geo,
    orientation="h",
    color=indicateur,
    title=f"{top_n} {niveau_geo.lower()} selon l'indicateur sélectionné",
)
fig_classement.update_layout(yaxis={"categoryorder": "total ascending"})
st.plotly_chart(fig_classement, use_container_width=True)

fig_dispersion = px.scatter(
    df_actuel,
    x="Niveau de vie médian (en euros)",
    y="Taux de pauvreté (en %) au seuil de 60 % de la médiane du niveau de vie",
    size="Nombre de personnes",
    hover_name=nom_geo,
    color="Part des ménages imposés (en %)",
    title=f"Croisement revenu médian / pauvreté ({niveau_geo.lower()})",
    labels={
        "Niveau de vie médian (en euros)": "Niveau de vie médian",
        "Taux de pauvreté (en %) au seuil de 60 % de la médiane du niveau de vie": "Taux de pauvreté",
        "Part des ménages imposés (en %)": "Ménages imposés (%)",
    },
)
st.plotly_chart(fig_dispersion, use_container_width=True)

selection_geo = st.selectbox(
    f"Comparer un {niveau_geo[:-1].lower()}",
    classement[nom_geo].tolist(),
)

ligne = df_actuel[df_actuel[nom_geo] == selection_geo].iloc[0]
comparatif = pd.DataFrame(
    {
        "Indicateur": [
            "Niveau de vie médian (en euros)",
            "Taux de pauvreté (en %) au seuil de 60 % de la médiane du niveau de vie",
            "Part des ménages imposés (en %)",
            "Rapport interdécile (D9/D1) du niveau de vie",
        ],
        selection_geo: [
            ligne["Niveau de vie médian (en euros)"],
            ligne["Taux de pauvreté (en %) au seuil de 60 % de la médiane du niveau de vie"],
            ligne["Part des ménages imposés (en %)"],
            ligne["Rapport interdécile (D9/D1) du niveau de vie"],
        ],
        f"Moyenne {niveau_geo.lower()}": [
            df_actuel["Niveau de vie médian (en euros)"].mean(),
            df_actuel["Taux de pauvreté (en %) au seuil de 60 % de la médiane du niveau de vie"].mean(),
            df_actuel["Part des ménages imposés (en %)"].mean(),
            df_actuel["Rapport interdécile (D9/D1) du niveau de vie"].mean(),
        ],
    }
)

fig_compare = px.bar(
    comparatif.melt(id_vars="Indicateur", var_name="Série", value_name="Valeur"),
    x="Indicateur",
    y="Valeur",
    color="Série",
    barmode="group",
    title=f"Comparaison de {selection_geo} avec la moyenne",
)
fig_compare.update_xaxes(tickangle=-20)
st.plotly_chart(fig_compare, use_container_width=True)

with st.expander("Table de données"):
    st.dataframe(df_actuel, use_container_width=True)
