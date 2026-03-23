import json
from pathlib import Path

import plotly.express as px
import streamlit as st

from utils.department_scores import calculer_scores_departements
from utils.ui_theme import apply_horizon_theme


st.set_page_config(page_title="Dashboard socio-economique", layout="wide")
apply_horizon_theme()

st.title("Dashboard socio-economique")
st.write("Ajuste les pondérations par thème pour comparer les départements selon tes priorités.")

scores = calculer_scores_departements()
geojson_departements = json.loads(
    Path("assets/departements.geojson").read_text(encoding="utf-8")
)
themes = {
    "Emploi": "Score emploi",
    "Étudiants": "Score étudiants",
    "Revenu": "Score revenu",
    "Santé": "Score santé",
    "Internet": "Score internet",
    "Criminalité": "Score criminalité",
    "Éducation": "Score éducation",
    "Immobilier": "Score immobilier",
}

selection_themes = st.multiselect(
    "Thèmes à prendre en compte",
    list(themes.keys()),
    default=list(themes.keys()),
)

if not selection_themes:
    st.warning("Sélectionne au moins un thème pour calculer le score global.")
    st.stop()

st.subheader("Pondérations")
colonnes_poids = st.columns(len(selection_themes))
poids = {}
for index, theme in enumerate(selection_themes):
    poids[theme] = colonnes_poids[index].slider(
        f"Poids {theme}",
        min_value=0.0,
        max_value=1.0,
        value=1.0,
        step=0.1,
    )

if sum(poids.values()) == 0:
    st.warning("La somme des pondérations ne peut pas être nulle.")
    st.stop()

poids_normalises = {theme: valeur / sum(poids.values()) for theme, valeur in poids.items()}
colonnes_selectionnees = [themes[theme] for theme in selection_themes]

numerateur = scores[colonnes_selectionnees[0]].where(
    scores[colonnes_selectionnees[0]].notna(), 0
) * 0
denominateur = numerateur.copy()
for theme in selection_themes:
    colonne = themes[theme]
    poids_theme = poids_normalises[theme]
    present = scores[colonne].notna()
    numerateur += scores[colonne].where(present, 0) * poids_theme
    denominateur += present.astype(float) * poids_theme

scores["Score global personnalisé"] = (numerateur / denominateur.where(denominateur > 0)).round(4)

scores = scores.sort_values("Score global personnalisé", ascending=False).reset_index(drop=True)

col1, col2, col3 = st.columns(3)
col1.metric("Départements comparés", f"{scores['Département'].nunique()}")
col2.metric("Meilleur département", scores.iloc[0]["Département"])
col3.metric("Score du leader", f"{scores.iloc[0]['Score global personnalisé']:.2f}")

scores_carte = scores[~scores["Département"].isin(["La Réunion", "Martinique"])].copy()

fig = px.choropleth(
    scores_carte,
    geojson=geojson_departements,
    locations="Département",
    featureidkey="properties.nom",
    color="Score global personnalisé",
    hover_name="Département",
    hover_data={
        "Région": True,
        "Score emploi": ":.2f",
        "Score étudiants": ":.2f",
        "Score revenu": ":.2f",
        "Score santé": ":.2f",
        "Score internet": ":.2f",
        "Score criminalité": ":.2f",
        "Score éducation": ":.2f",
        "Score immobilier": ":.2f",
        "Score global personnalisé": ":.2f",
    },
    color_continuous_scale=[
        [0.0, "#b2182b"],
        [0.25, "#ef8a62"],
        [0.5, "#fddbc7"],
        [0.75, "#d9f0d3"],
        [1.0, "#1a9850"],
    ],
    range_color=(0, 1),
    labels={"Score global personnalisé": "Note"},
)
fig.update_geos(fitbounds="locations", visible=False, projection={"type": "mercator"})
fig.update_traces(
    marker_line_color="rgba(255,255,255,0.18)",
    marker_line_width=0.6,
    hoverlabel={"bgcolor": "#161a23", "font_color": "#f5f7fa"},
)
fig.update_layout(
    template="plotly_dark",
    height=700,
    margin={"l": 0, "r": 0, "t": 20, "b": 0},
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font={"color": "#e8edf2"},
    coloraxis_colorbar={
        "title": {"text": "Note", "font": {"color": "#e8edf2"}},
        "bgcolor": "rgba(0,0,0,0)",
        "tickcolor": "#cfd6df",
        "tickfont": {"color": "#cfd6df"},
    },
)
st.plotly_chart(fig, use_container_width=True)

st.caption(
    "La carte couvre les départements de métropole et de Corse présents dans le GeoJSON local. "
    "La Réunion et la Martinique restent dans le tableau ci-dessous."
)

st.subheader("Classement personnalisé")
st.dataframe(
    scores[
        [
            "Département",
            "Région",
            "Score emploi",
            "Score étudiants",
            "Score revenu",
            "Score santé",
            "Score internet",
            "Score criminalité",
            "Score éducation",
            "Score immobilier",
            "Score global personnalisé",
        ]
    ].style.format(
        {
            "Score emploi": "{:.2f}",
            "Score étudiants": "{:.2f}",
            "Score revenu": "{:.2f}",
            "Score santé": "{:.2f}",
            "Score internet": "{:.2f}",
            "Score criminalité": "{:.2f}",
            "Score éducation": "{:.2f}",
            "Score immobilier": "{:.2f}",
            "Score global personnalisé": "{:.2f}",
        }
    ),
    use_container_width=True,
)

st.caption(
    "Lecture des notes: 0 = moins favorable dans l'échantillon, 1 = plus favorable. "
    "Le score global personnalisé est une moyenne pondérée des thèmes sélectionnés."
)
