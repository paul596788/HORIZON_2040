import pandas as pd
import plotly.express as px
import streamlit as st

from utils.excel_helpers import (
    charger_excel,
    colonnes_sans_unnamed,
    get_global_department_selection,
    nettoyer_colonnes,
    render_global_department_selector,
)


st.title("Accès aux soins et offre de santé")
render_global_department_selector(
    caption="La sélection est partagée entre les pages. Elle pilote ici les comparaisons départementales."
)

fichier_sante = "pages/tables/sante/santé_data.xlsx"
fichier_hopital = "pages/tables/sante/analyse_acces_hopital_2010.xlsx"

df_medecins = nettoyer_colonnes(
    colonnes_sans_unnamed(charger_excel(fichier_sante, sheet_name="medecin pour 100 000, 01,23"))
)
df_hospitalisation = nettoyer_colonnes(
    colonnes_sans_unnamed(charger_excel(fichier_sante, sheet_name="recours hospitalisa 10000hab"))
)
df_chirurgie = nettoyer_colonnes(
    colonnes_sans_unnamed(charger_excel(fichier_sante, sheet_name="% chirurgie ambulatoire"))
)
df_medecins_g = nettoyer_colonnes(
    colonnes_sans_unnamed(charger_excel(fichier_sante, sheet_name="medecin G pour 100 000"))
)
df_medecins_s = nettoyer_colonnes(
    colonnes_sans_unnamed(charger_excel(fichier_sante, sheet_name="medecin spé pour 100 000"))
)
df_cpts = nettoyer_colonnes(
    colonnes_sans_unnamed(charger_excel(fichier_sante, sheet_name="couverture de pop par une CPTS"))
)
df_hopital = nettoyer_colonnes(charger_excel(fichier_hopital, sheet_name="Résumé_région"))

df_medecins = df_medecins[df_medecins["Départements"].notna() & (df_medecins["Départements"] != "France entière")].copy()
for colonne in ["Omnipraticiens 2020", "Spécialistes 2020", "Omnipraticiens 2021", "Spécialistes 2021"]:
    df_medecins[colonne] = pd.to_numeric(df_medecins[colonne], errors="coerce")

for df_densite in [df_medecins_g, df_medecins_s]:
    df_densite.columns = [str(col).strip() for col in df_densite.columns]
    for colonne in [col for col in df_densite.columns if "densite_" in col]:
        df_densite[colonne] = pd.to_numeric(df_densite[colonne], errors="coerce")

for colonne in ["Chirurgie", "Médecine", "SMR", "PSY"]:
    df_hospitalisation[colonne] = pd.to_numeric(df_hospitalisation[colonne], errors="coerce")

for colonne in ["moyenne_minutes", "mediane_minutes", "min_minutes", "max_minutes"]:
    df_hopital[colonne] = pd.to_numeric(df_hopital[colonne], errors="coerce")

df_chirurgie["taux %"] = pd.to_numeric(df_chirurgie["taux %"], errors="coerce") * 100
df_cpts["Taux de la couverture\nde la population\npar une CPTS"] = pd.to_numeric(
    df_cpts["Taux de la couverture\nde la population\npar une CPTS"], errors="coerce"
) * 100
departements_specialistes = set(df_medecins_s["Département"].dropna())
departements_selectionnes = get_global_department_selection(df_medecins_g["Département"].dropna().unique())

onglet1, onglet2, onglet3 = st.tabs(
    ["Médecins", "Hospitalisation", "Accès territorial"]
)

with onglet1:
    type_medecin = st.radio(
        "Type de densité",
        ["Omnipraticiens", "Spécialistes"],
        horizontal=True,
    )

    colonne_2020 = f"{type_medecin} 2020"
    colonne_2021 = f"{type_medecin} 2021"
    classement = (
        df_medecins[["Départements", colonne_2020, colonne_2021]]
        .dropna()
    )
    if departements_selectionnes:
        classement = classement[classement["Départements"].isin(departements_selectionnes)]
    classement = classement.sort_values(colonne_2021, ascending=False).head(20)

    fig_medecins = px.bar(
        classement,
        x="Départements",
        y=[colonne_2020, colonne_2021],
        barmode="group",
        title=f"Densité de {type_medecin.lower()} pour 100 000 habitants",
        labels={"value": "Densité", "variable": "Année"},
    )
    fig_medecins.update_xaxes(tickangle=-45)
    st.plotly_chart(fig_medecins, use_container_width=True)

    departement_options = sorted(df_medecins_g["Département"].dropna().unique())
    if departements_selectionnes:
        departement_options = [dep for dep in departement_options if dep in departements_selectionnes]
    departement_index = 0
    if departements_selectionnes and departements_selectionnes[0] in departement_options:
        departement_index = departement_options.index(departements_selectionnes[0])
    departement = st.selectbox(
        "Département à comparer",
        departement_options,
        index=departement_index,
    )
    historique = pd.DataFrame(
        {
            "Année": [2012, 2014, 2024, 2012, 2014, 2024],
            "Densité": [
                df_medecins_g.loc[df_medecins_g["Département"] == departement, "densite_2012"].iloc[0],
                df_medecins_g.loc[df_medecins_g["Département"] == departement, "densite_2014"].iloc[0],
                df_medecins_g.loc[df_medecins_g["Département"] == departement, "densite_2024"].iloc[0],
                df_medecins_s.loc[df_medecins_s["Département"] == departement, "densite_2012"].iloc[0]
                if departement in departements_specialistes
                else None,
                df_medecins_s.loc[df_medecins_s["Département"] == departement, "densite_2014"].iloc[0]
                if departement in departements_specialistes
                else None,
                df_medecins_s.loc[df_medecins_s["Département"] == departement, "densite_2024"].iloc[0]
                if departement in departements_specialistes
                else None,
            ],
            "Catégorie": [
                "Généralistes",
                "Généralistes",
                "Généralistes",
                "Spécialistes",
                "Spécialistes",
                "Spécialistes",
            ],
        }
    ).dropna()

    fig_historique = px.line(
        historique,
        x="Année",
        y="Densité",
        color="Catégorie",
        markers=True,
        title=f"Évolution de la densité médicale pour {departement}",
    )
    st.plotly_chart(fig_historique, use_container_width=True)

with onglet2:
    fig_hospit = px.bar(
        df_hospitalisation.dropna(subset=["Région", "Chirurgie", "Médecine", "SMR", "PSY"]).head(18),
        x="Région",
        y=["Chirurgie", "Médecine", "SMR", "PSY"],
        barmode="group",
        title="Recours hospitaliers standardisés par région",
    )
    fig_hospit.update_xaxes(tickangle=-45)
    st.plotly_chart(fig_hospit, use_container_width=True)

    fig_ambulatoire = px.bar(
        df_chirurgie.sort_values("taux %", ascending=False),
        x="région",
        y="taux %",
        color="taux %",
        title="Part de chirurgie ambulatoire par région",
        labels={"taux %": "Taux (%)"},
    )
    fig_ambulatoire.update_xaxes(tickangle=-35)
    st.plotly_chart(fig_ambulatoire, use_container_width=True)

with onglet3:
    fig_hopital = px.bar(
        df_hopital.sort_values("moyenne_minutes", ascending=False),
        x="region",
        y="moyenne_minutes",
        title="Temps moyen d'accès à l'hôpital par région",
        labels={"region": "Région", "moyenne_minutes": "Temps moyen (minutes)"},
    )
    fig_hopital.update_xaxes(tickangle=-35)
    st.plotly_chart(fig_hopital, use_container_width=True)

    fig_cpts = px.bar(
        df_cpts.sort_values(
            "Taux de la couverture\nde la population\npar une CPTS",
            ascending=False,
        ),
        x="Libellé Région",
        y="Taux de la couverture\nde la population\npar une CPTS",
        color="Taux de la couverture\nde la population\npar une CPTS",
        title="Couverture de la population par une CPTS",
        labels={
            "Libellé Région": "Région",
            "Taux de la couverture\nde la population\npar une CPTS": "Couverture (%)",
        },
    )
    fig_cpts.update_xaxes(tickangle=-35)
    st.plotly_chart(fig_cpts, use_container_width=True)
