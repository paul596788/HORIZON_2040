import json
from pathlib import Path

import pandas as pd
import streamlit as st

from utils.excel_helpers import (
    charger_csv,
    charger_excel,
    charger_geojson,
    colonnes_sans_unnamed,
    nettoyer_colonnes,
)


def _normaliser_serie(serie, inverse=False):
    serie = pd.to_numeric(serie, errors="coerce")
    minimum = serie.min()
    maximum = serie.max()

    if pd.isna(minimum) or pd.isna(maximum):
        return pd.Series(0.0, index=serie.index)

    if maximum == minimum:
        score = pd.Series(1.0, index=serie.index)
    else:
        score = (serie - minimum) / (maximum - minimum)

    if inverse:
        score = 1 - score

    return score.clip(0, 1)


def _moyenne_ponderee_disponible(df, colonnes_poids):
    numerateur = pd.Series(0.0, index=df.index)
    denominateur = pd.Series(0.0, index=df.index)

    for colonne, poids in colonnes_poids.items():
        present = df[colonne].notna()
        numerateur.loc[present] += df.loc[present, colonne] * poids
        denominateur.loc[present] += poids

    return (numerateur / denominateur.where(denominateur > 0)).round(4)


def _score_emploi():
    df = nettoyer_colonnes(
        charger_excel("pages/tables/emplois_et_chomage/Demandeurs_emploi_taux_chomage_2000_2025.xlsx")
    )
    taux_cols = [col for col in df.columns if "Taux de chomage" in col or "Taux de chômage" in col]

    df_long = df.melt(
        id_vars=["Département"],
        value_vars=taux_cols,
        var_name="Année",
        value_name="Taux de chômage",
    )
    df_long["Année"] = df_long["Année"].astype(str).str.extract(r"(\d{4})")
    df_long = df_long.dropna(subset=["Année"])
    df_long["Année"] = df_long["Année"].astype(int)
    df_long["Taux de chômage"] = pd.to_numeric(
        df_long["Taux de chômage"].astype(str).str.replace(",", ".", regex=False),
        errors="coerce",
    )

    premiere_annee = int(df_long["Année"].min())
    derniere_annee = int(df_long["Année"].max())

    debut = (
        df_long[df_long["Année"] == premiere_annee][["Département", "Taux de chômage"]]
        .rename(columns={"Taux de chômage": "Taux début"})
    )
    fin = (
        df_long[df_long["Année"] == derniere_annee][["Département", "Taux de chômage"]]
        .rename(columns={"Taux de chômage": "Taux fin"})
    )

    score = debut.merge(fin, on="Département", how="inner")
    score["Amélioration chômage"] = score["Taux début"] - score["Taux fin"]
    score["Score emploi"] = (
        0.7 * _normaliser_serie(score["Taux fin"], inverse=True)
        + 0.3 * _normaliser_serie(score["Amélioration chômage"])
    ).round(4)
    return score[["Département", "Score emploi", "Taux fin", "Amélioration chômage"]]


def _score_etudiants():
    df = nettoyer_colonnes(
        charger_excel("pages/tables/etudiants/fr-esr-atlas_regional-effectifs-d-etudiants-inscrits_agregeables.xlsx")
    )
    df["Nombre total d’étudiants inscrits"] = pd.to_numeric(
        df["Nombre total d’étudiants inscrits"], errors="coerce"
    )
    df["Année civile concernée"] = pd.to_numeric(df["Année civile concernée"], errors="coerce")

    agg = (
        df.groupby(["Département", "Année civile concernée"], as_index=False)[
            "Nombre total d’étudiants inscrits"
        ]
        .sum()
        .dropna()
    )

    premiere_annee = int(agg["Année civile concernée"].min())
    derniere_annee = int(agg["Année civile concernée"].max())

    debut = (
        agg[agg["Année civile concernée"] == premiere_annee][
            ["Département", "Nombre total d’étudiants inscrits"]
        ]
        .rename(columns={"Nombre total d’étudiants inscrits": "Étudiants début"})
    )
    fin = (
        agg[agg["Année civile concernée"] == derniere_annee][
            ["Département", "Nombre total d’étudiants inscrits"]
        ]
        .rename(columns={"Nombre total d’étudiants inscrits": "Étudiants fin"})
    )

    score = debut.merge(fin, on="Département", how="inner")
    score["Croissance étudiante"] = score["Étudiants fin"] - score["Étudiants début"]
    score["Score étudiants"] = (
        0.7 * _normaliser_serie(score["Étudiants fin"])
        + 0.3 * _normaliser_serie(score["Croissance étudiante"])
    ).round(4)
    return score[["Département", "Score étudiants", "Étudiants fin", "Croissance étudiante"]]


def _score_revenu():
    df = nettoyer_colonnes(charger_excel("pages/tables/revenu/base-cc-filosofi-2021-geo2025.xlsx", sheet_name="DEP"))
    colonnes = [
        "Niveau de vie médian (en euros)",
        "Taux de pauvreté (en %) au seuil de 60 % de la médiane du niveau de vie",
        "Part des ménages imposés (en %)",
        "Rapport interdécile (D9/D1) du niveau de vie",
    ]
    for colonne in colonnes:
        df[colonne] = pd.to_numeric(df[colonne], errors="coerce")

    score = df.rename(columns={"Géographie": "Département"}).copy()
    score["Score revenu"] = (
        0.4 * _normaliser_serie(score["Niveau de vie médian (en euros)"])
        + 0.3
        * _normaliser_serie(
            score["Taux de pauvreté (en %) au seuil de 60 % de la médiane du niveau de vie"],
            inverse=True,
        )
        + 0.2 * _normaliser_serie(score["Part des ménages imposés (en %)"])
        + 0.1 * _normaliser_serie(score["Rapport interdécile (D9/D1) du niveau de vie"], inverse=True)
    ).round(4)
    return score[
        [
            "Département",
            "Score revenu",
            "Niveau de vie médian (en euros)",
            "Taux de pauvreté (en %) au seuil de 60 % de la médiane du niveau de vie",
        ]
    ]


def _score_sante():
    df_regions = nettoyer_colonnes(
        charger_excel("pages/tables/etudiants/fr-esr-atlas_regional-effectifs-d-etudiants-inscrits_agregeables.xlsx")
    )
    departement_region = (
        df_regions[["Département", "Région"]].dropna().drop_duplicates(subset=["Département"])
    )

    df_medecins_g = nettoyer_colonnes(
        colonnes_sans_unnamed(charger_excel("pages/tables/sante/santé_data.xlsx", sheet_name="medecin G pour 100 000"))
    )
    df_medecins_s = nettoyer_colonnes(
        colonnes_sans_unnamed(charger_excel("pages/tables/sante/santé_data.xlsx", sheet_name="medecin spé pour 100 000"))
    )
    df_chirurgie = nettoyer_colonnes(
        colonnes_sans_unnamed(charger_excel("pages/tables/sante/santé_data.xlsx", sheet_name="% chirurgie ambulatoire"))
    )
    df_cpts = nettoyer_colonnes(
        colonnes_sans_unnamed(charger_excel("pages/tables/sante/santé_data.xlsx", sheet_name="couverture de pop par une CPTS"))
    )

    for df_densite in [df_medecins_g, df_medecins_s]:
        df_densite.columns = [str(col).strip() for col in df_densite.columns]
        for colonne in [col for col in df_densite.columns if "densite_" in col]:
            df_densite[colonne] = pd.to_numeric(df_densite[colonne], errors="coerce")

    df_chirurgie["taux %"] = pd.to_numeric(df_chirurgie["taux %"], errors="coerce")
    df_cpts["Taux de la couverture\nde la population\npar une CPTS"] = pd.to_numeric(
        df_cpts["Taux de la couverture\nde la population\npar une CPTS"], errors="coerce"
    )

    score = departement_region.merge(df_medecins_g[["Département", "densite_2024"]], on="Département", how="left")
    score = score.merge(
        df_medecins_s[["Département", "densite_2024"]].rename(columns={"densite_2024": "densite_2024_spec"}),
        on="Département",
        how="left",
    )
    score = score.merge(
        df_chirurgie.rename(columns={"région": "Région", "taux %": "chirurgie_ambulatoire"}),
        on="Région",
        how="left",
    )
    score = score.merge(
        df_cpts.rename(
            columns={
                "Libellé Région": "Région",
                "Taux de la couverture\nde la population\npar une CPTS": "couverture_cpts",
            }
        ),
        on="Région",
        how="left",
    )

    score["score_densite_g"] = _normaliser_serie(score["densite_2024"])
    score["score_densite_s"] = _normaliser_serie(score["densite_2024_spec"])
    score["score_cpts"] = _normaliser_serie(score["couverture_cpts"])
    score["score_chirurgie"] = _normaliser_serie(score["chirurgie_ambulatoire"])
    score["Score santé"] = _moyenne_ponderee_disponible(
        score,
        {
            "score_densite_g": 0.4,
            "score_densite_s": 0.25,
            "score_cpts": 0.2,
            "score_chirurgie": 0.15,
        },
    )

    return score[
        [
            "Département",
            "Région",
            "Score santé",
            "densite_2024",
            "densite_2024_spec",
            "couverture_cpts",
            "chirurgie_ambulatoire",
        ]
    ]


def _score_internet():
    df = charger_csv("pages/tables/Internet.csv")
    df["Dep_name"] = df["Dep_name"].replace(
        {
            "Côtes d'Armor": "Côtes-d'Armor",
            "Seine-St-Denis": "Seine-Saint-Denis",
            "Val-D'Oise": "Val-d'Oise",
        }
    )
    df["Coefficient"] = pd.to_numeric(df["Coefficient"], errors="coerce")
    df["Fibre"] = pd.to_numeric(df["Fibre"], errors="coerce")
    df["Score internet"] = _normaliser_serie(df["Coefficient"]).round(4)
    return df.rename(columns={"Dep_name": "Département"})[
        ["Département", "Score internet", "Coefficient", "Fibre", "Nombre de locaux"]
    ]


def _score_criminalite():
    df = charger_csv("pages/tables/CrimebyDept_2040.csv")
    df["Coefficient"] = pd.to_numeric(df["Coefficient"], errors="coerce")
    df["nombre"] = pd.to_numeric(df["nombre"], errors="coerce")
    df["Score criminalité"] = _normaliser_serie(df["Coefficient"]).round(4)
    return df.rename(columns={"dep_name": "Département"})[
        ["Département", "Score criminalité", "Coefficient", "nombre"]
    ]


def _score_education():
    geojson_departements = charger_geojson("pages/tables/departements.geojson")
    code_to_name = {
        feature["properties"]["code"]: feature["properties"]["nom"]
        for feature in geojson_departements["features"]
    }

    df = charger_csv("pages/tables/Education.csv")
    df["num_dep"] = df["num_dep"].astype(str).str.zfill(2)
    df["Département"] = df["num_dep"].map(code_to_name)
    df["coefficient"] = pd.to_numeric(df["coefficient"], errors="coerce")
    df["nb_stud_total"] = pd.to_numeric(df["nb_stud_total"], errors="coerce")
    df["POP_2024"] = pd.to_numeric(df["POP_2024"], errors="coerce")
    df["Score éducation"] = _normaliser_serie(df["coefficient"]).round(4)
    return df[
        ["Département", "Score éducation", "coefficient", "nb_stud_total", "POP_2024"]
    ]


def _score_immobilier():
    df = charger_csv("pages/tables/Real_Estate_Prices.csv", sep=";")
    df["Coefficient"] = pd.to_numeric(df["Coefficient"], errors="coerce")
    df["Price2025"] = pd.to_numeric(df["Price2025"], errors="coerce")
    df["Price2040"] = pd.to_numeric(df["Price2040"], errors="coerce")
    df["Score immobilier"] = _normaliser_serie(df["Coefficient"]).round(4)
    return df.rename(columns={"dep_name": "Département"})[
        ["Département", "Score immobilier", "Coefficient", "Price2025", "Price2040"]
    ]

@st.cache_data
def calculer_scores_departements():
    score_emploi = _score_emploi()
    score_etudiants = _score_etudiants()
    score_revenu = _score_revenu()
    score_sante = _score_sante()
    score_internet = _score_internet()
    score_criminalite = _score_criminalite()
    score_education = _score_education()
    score_immobilier = _score_immobilier()

    scores = score_revenu.merge(score_emploi, on="Département", how="left")
    scores = scores.merge(score_etudiants, on="Département", how="left")
    scores = scores.merge(score_sante, on="Département", how="left")
    scores = scores.merge(score_internet, on="Département", how="left")
    scores = scores.merge(score_criminalite, on="Département", how="left")
    scores = scores.merge(score_education, on="Département", how="left")
    scores = scores.merge(score_immobilier, on="Département", how="left")

    scores["Score global"] = _moyenne_ponderee_disponible(
        scores,
        {
            "Score emploi": 1.0,
            "Score étudiants": 1.0,
            "Score revenu": 1.0,
            "Score santé": 1.0,
            "Score internet": 1.0,
            "Score criminalité": 1.0,
            "Score éducation": 1.0,
            "Score immobilier": 1.0,
        },
    )

    return scores.sort_values("Score global", ascending=False).reset_index(drop=True)
