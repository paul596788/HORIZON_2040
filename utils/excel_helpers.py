from pathlib import Path
import json

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent

@st.cache_data
def charger_excel(chemin_fichier, sheet_name=0):
    fichier = BASE_DIR / chemin_fichier
    return pd.read_excel(fichier, sheet_name=sheet_name)

@st.cache_data
def charger_csv(chemin_fichier, **kwargs):
    fichier = BASE_DIR / chemin_fichier
    return pd.read_csv(fichier, **kwargs)

@st.cache_data
def charger_geojson(chemin_fichier):
    fichier = BASE_DIR / chemin_fichier
    return json.loads(fichier.read_text(encoding="utf-8"))

def nettoyer_colonnes(df):
    df.columns = [str(col).strip() for col in df.columns]
    return df

def colonnes_sans_unnamed(df):
    return df.loc[:, ~df.columns.astype(str).str.contains(r"^Unnamed:", na=False)].copy()

def convertir_numerique(df, colonnes):
    for colonne in colonnes:
        if colonne in df.columns:
            df[colonne] = pd.to_numeric(df[colonne], errors="coerce")
    return df
