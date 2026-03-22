from pathlib import Path
import json
import unicodedata

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent
EXCLUDED_DEPARTMENT_CODES = {"972", "974"}
EXCLUDED_TERRITORY_NAMES = {"la reunion", "reunion", "martinique"}
GLOBAL_DEPARTMENT_SELECTION_KEY = "global_selected_departements"


def _normaliser_texte(valeur):
    if pd.isna(valeur):
        return ""

    texte = unicodedata.normalize("NFKD", str(valeur).strip().lower())
    texte = "".join(caractere for caractere in texte if not unicodedata.combining(caractere))
    texte = texte.replace("-", " ").replace("'", " ")
    return " ".join(texte.split())


def _normaliser_cle_colonne(colonne):
    return _normaliser_texte(colonne).replace(" ", "_")


def _code_exclu(valeur):
    if pd.isna(valeur):
        return False

    texte = str(valeur).strip().upper()
    if texte in EXCLUDED_DEPARTMENT_CODES:
        return True

    chiffres = "".join(caractere for caractere in texte if caractere.isdigit())
    return chiffres in EXCLUDED_DEPARTMENT_CODES


def filtrer_territoires_exclus_df(df):
    if not isinstance(df, pd.DataFrame) or df.empty:
        return df

    colonnes_nom = {
        "departement",
        "dep_name",
        "nom",
        "geographie",
        "region",
        "region_name",
        "libelle_region",
        "departement_label",
    }
    colonnes_code = {
        "code",
        "num_dep",
        "dep_num",
        "code_departement",
        "code_dep",
    }

    masque_exclu = pd.Series(False, index=df.index)

    for colonne in df.columns:
        cle = _normaliser_cle_colonne(colonne)

        if cle in colonnes_nom:
            masque_exclu |= df[colonne].map(_normaliser_texte).isin(EXCLUDED_TERRITORY_NAMES)

        if cle in colonnes_code:
            masque_exclu |= df[colonne].map(_code_exclu)

    if not masque_exclu.any():
        return df

    return df.loc[~masque_exclu].copy()


def filtrer_territoires_exclus_geojson(geojson):
    if not isinstance(geojson, dict) or "features" not in geojson:
        return geojson

    features_filtrees = []
    for feature in geojson.get("features", []):
        proprietes = feature.get("properties", {})
        nom = proprietes.get("nom", "")
        code = proprietes.get("code", "")
        if _normaliser_texte(nom) in EXCLUDED_TERRITORY_NAMES or _code_exclu(code):
            continue
        features_filtrees.append(feature)

    geojson_filtre = dict(geojson)
    geojson_filtre["features"] = features_filtrees
    return geojson_filtre


def filtrer_codes_exclus(codes):
    if not codes:
        return []
    return [code for code in codes if not _code_exclu(code)]


@st.cache_data
def lister_departements_france():
    geojson = charger_geojson("pages/tables/departements.geojson")
    noms = {
        feature.get("properties", {}).get("nom")
        for feature in geojson.get("features", [])
        if feature.get("properties", {}).get("nom")
    }
    return sorted(noms)


def get_global_department_selection(available_departments=None):
    selected = st.session_state.get(GLOBAL_DEPARTMENT_SELECTION_KEY, [])
    if not isinstance(selected, list):
        selected = []

    selected = [str(departement) for departement in selected if str(departement).strip()]

    if available_departments is None:
        return selected

    available_set = {
        str(departement)
        for departement in available_departments
        if not pd.isna(departement) and str(departement).strip()
    }
    return [departement for departement in selected if departement in available_set]


def render_global_department_selector(
    title="Sélection des départements",
    label="Sélectionne jusqu'à 4 départements",
    placeholder="Tape pour rechercher un département...",
    caption=None,
    max_items=4,
):
    options = lister_departements_france()
    current_selection = [departement for departement in get_global_department_selection() if departement in options]
    st.session_state[GLOBAL_DEPARTMENT_SELECTION_KEY] = current_selection

    if title:
        st.subheader(title)

    selected = st.multiselect(
        label,
        options=options,
        key=GLOBAL_DEPARTMENT_SELECTION_KEY,
        placeholder=placeholder,
    )

    if len(selected) > max_items:
        selected = selected[:max_items]
        st.session_state[GLOBAL_DEPARTMENT_SELECTION_KEY] = selected
        st.info("Comparaison limitée à 4 départements pour garder la lecture lisible.")

    if caption:
        st.caption(caption)

    return selected


def ajouter_surlignage_departements(
    fig,
    geojson,
    locations,
    featureidkey,
    line_color="#f8fafc",
    line_width=3.2,
    halo_color="rgba(15,23,42,0.98)",
    halo_width=5.2,
):
    if not locations:
        return fig

    trace_kwargs = {
        "geojson": geojson,
        "locations": locations,
        "featureidkey": featureidkey,
        "z": [1] * len(locations),
        "colorscale": [[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
        "showscale": False,
        "hoverinfo": "skip",
        "showlegend": False,
        "name": "Sélection",
    }

    fig.add_trace(
        go.Choropleth(
            **trace_kwargs,
            marker_line_color=halo_color,
            marker_line_width=halo_width,
        )
    )
    fig.add_trace(
        go.Choropleth(
            **trace_kwargs,
            marker_line_color=line_color,
            marker_line_width=line_width,
        )
    )
    return fig


def styliser_carte_departements(
    fig,
    legend_title,
    *,
    height=680,
    hovertemplate=None,
    tickformat=None,
    marker_line_color="rgba(255,255,255,0.25)",
    marker_line_width=0.9,
    colorbar_len=0.78,
    colorbar_thickness=14,
):
    fig.update_geos(
        fitbounds="locations",
        visible=False,
        projection={"type": "mercator"},
        bgcolor="rgba(0,0,0,0)",
    )

    trace_style = {
        "marker_line_color": marker_line_color,
        "marker_line_width": marker_line_width,
    }
    if hovertemplate is not None:
        trace_style["hovertemplate"] = hovertemplate
    fig.update_traces(**trace_style)

    colorbar = {
        "title": {"text": legend_title, "font": {"color": "#e8edf2"}},
        "tickfont": {"color": "#cfd6df"},
        "bgcolor": "rgba(0,0,0,0)",
        "len": colorbar_len,
        "thickness": colorbar_thickness,
        "outlinewidth": 0,
    }
    if tickformat is not None:
        colorbar["tickformat"] = tickformat

    fig.update_layout(
        template="plotly_dark",
        height=height,
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#e8edf2"},
        coloraxis_colorbar=colorbar,
        hoverlabel={
            "bgcolor": "#0f172a",
            "font_color": "#f8fafc",
            "bordercolor": "rgba(255,255,255,0.15)",
        },
    )
    return fig

@st.cache_data
def charger_excel(chemin_fichier, sheet_name=0):
    fichier = BASE_DIR / chemin_fichier
    contenu = pd.read_excel(fichier, sheet_name=sheet_name)
    if isinstance(contenu, dict):
        return {nom: filtrer_territoires_exclus_df(df) for nom, df in contenu.items()}
    return filtrer_territoires_exclus_df(contenu)

@st.cache_data
def charger_csv(chemin_fichier, **kwargs):
    fichier = BASE_DIR / chemin_fichier
    return filtrer_territoires_exclus_df(pd.read_csv(fichier, **kwargs))

@st.cache_data
def charger_geojson(chemin_fichier):
    fichier = BASE_DIR / chemin_fichier
    return filtrer_territoires_exclus_geojson(json.loads(fichier.read_text(encoding="utf-8")))

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
