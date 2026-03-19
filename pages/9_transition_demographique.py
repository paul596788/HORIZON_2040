import pandas as pd
import plotly.express as px
import streamlit as st

from utils.excel_helpers import charger_csv, charger_geojson


st.set_page_config(page_title="Transition démographique 2040", layout="wide")

st.markdown(
    """
<style>
.stApp {
background: radial-gradient(1200px 800px at 20% 0%, #111827 0%, #0b0f15 45%, #090c12 100%);
color: #e5e7eb;
}
.block-container {
padding-top: 1.6rem;
padding-bottom: 3rem;
max-width: 1280px;
}
h1 {
font-weight: 700;
letter-spacing: -0.02em;
}
h2, h3 {
color: #e2e8f0;
font-weight: 600;
}
div[data-testid="stMetric"] {
background: rgba(255,255,255,0.03);
border: 1px solid rgba(255,255,255,0.08);
border-radius: 14px;
padding: 14px 16px;
}
div[data-testid="stPlotlyChart"] {
background: rgba(255,255,255,0.01);
border: 1px solid rgba(255,255,255,0.06);
border-radius: 16px;
padding: 6px;
}
.story-card {
background: linear-gradient(180deg, rgba(30,41,59,0.88) 0%, rgba(15,23,42,0.9) 100%);
border: 1px solid rgba(148,163,184,0.18);
border-radius: 18px;
padding: 18px 18px 14px 18px;
min-height: 100%;
}
.story-kicker {
color: #cbd5e1;
font-size: 0.83rem;
text-transform: uppercase;
letter-spacing: 0.08em;
margin-bottom: 0.6rem;
}
.story-title {
font-size: 1.35rem;
font-weight: 700;
color: #f8fafc;
line-height: 1.2;
margin-bottom: 0.8rem;
}
.story-body {
color: #dbe4ee;
font-size: 0.98rem;
line-height: 1.6;
}
.story-list {
margin-top: 0.9rem;
padding-left: 1rem;
color: #dbe4ee;
}
.story-list li {
margin-bottom: 0.45rem;
}
.section-spacer { height: 18px; }
</style>
""",
    unsafe_allow_html=True,
)


def _format_codes(series: pd.Series) -> pd.Series:
    cleaned = series.astype(str).str.strip().str.upper()
    return cleaned.apply(lambda code: code.zfill(2) if code.isdigit() else code)


def _quadrant(row: pd.Series, x_cut: float, y_cut: float) -> str:
    if row["confort_thermique_2040"] <= x_cut and row["indice_vieillissement"] <= y_cut:
        return "Double tension"
    if row["confort_thermique_2040"] <= x_cut and row["indice_vieillissement"] > y_cut:
        return "Jeunes mais exposés"
    if row["confort_thermique_2040"] > x_cut and row["indice_vieillissement"] <= y_cut:
        return "Vieillissants mais tempérés"
    return "Profil plus favorable"


st.title("Transition démographique")
st.caption(
    "Le vieillissement de la population redessine les dynamiques territoriales et crée "
    "des déséquilibres structurels entre départements."
)

with st.expander("Méthodologie & sources", expanded=False):
    tab_methodo, tab_sources = st.tabs(["Méthodologie", "Sources"])
    with tab_methodo:
        st.markdown(
            """
### Vulnérabilité démographique

L’indice mesure la structure d’âge des territoires à partir d’un indicateur simple de vieillissement.

```text
indice_vieillissement = 1 - (population 75+ / population 0-24)
```

Lecture :
- valeur élevée → territoire plus jeune
- valeur faible → territoire plus vieillissant

Pourquoi c’est utile :
- les populations âgées sont plus exposées aux vagues de chaleur
- elles sont plus sensibles aux risques sanitaires
- elles disposent souvent d’une capacité d’adaptation plus faible face aux événements extrêmes
"""
        )
    with tab_sources:
        st.markdown(
            """
### Sources
- INSEE — données démographiques
"""
        )

demography_label = "Indice démographique"
demography_label_with_hint = "Indice démographique (1 = plus jeune)"

old_df = charger_csv("pages/tables/Old_df.csv")
temp_df = charger_csv("pages/tables/Temperature_2040_df.csv")
departements = charger_geojson("pages/tables/departements.geojson")

old_df["code"] = _format_codes(old_df["code"])
temp_df["code"] = _format_codes(temp_df["code"])
old_df = old_df[old_df["code"] != "M"].copy()
old_df["indice_vieillissement"] = pd.to_numeric(old_df["indice de vieillissement"], errors="coerce")

temp_df["score_temperature"] = (
    0.60 * temp_df["nuits_tropicales"] + 0.40 * temp_df["jours_sup_35C"]
)
temp_df["confort_thermique_2040"] = temp_df["score_temperature"]

geo_names = {
    feature["properties"]["code"]: feature["properties"]["nom"]
    for feature in departements.get("features", [])
}

df = (
    old_df[["code", "Departement", "indice_vieillissement"]]
    .merge(
        temp_df[["code", "confort_thermique_2040"]],
        on="code",
        how="left",
    )
    .copy()
)
df["Departement"] = df["code"].map(geo_names).fillna(df["Departement"])
df = df[df["code"].isin(geo_names)].copy()
df["departement_label"] = df["Departement"] + " (" + df["code"] + ")"

age_mean = float(df["indice_vieillissement"].mean())
age_median = float(df["indice_vieillissement"].median())
age_std = float(df["indice_vieillissement"].std())
comfort_median = float(df["confort_thermique_2040"].median())
df["profil_strategique"] = df.apply(_quadrant, axis=1, x_cut=comfort_median, y_cut=age_median)
df["double_pression_score"] = (
    (1 - df["indice_vieillissement"]) + (1 - df["confort_thermique_2040"])
)

youngest_df = df.nlargest(5, "indice_vieillissement").copy()
oldest_df = df.nsmallest(5, "indice_vieillissement").copy()
double_tension_df = df[df["profil_strategique"] == "Double tension"].copy()
double_tension_count = int(len(double_tension_df))

aging_color_scale = [
    (0.0, "#0b1730"),
    (0.48, "#7e8796"),
    (1.0, "#b87333"),
]

fig_map = px.choropleth(
    df,
    geojson=departements,
    locations="code",
    featureidkey="properties.code",
    color="indice_vieillissement",
    color_continuous_scale=aging_color_scale,
    range_color=(0, 1),
    custom_data=["Departement", "code", "indice_vieillissement"],
)
fig_map.update_geos(
    fitbounds="locations",
    visible=False,
    projection={"type": "mercator"},
    bgcolor="rgba(0,0,0,0)",
)
fig_map.update_traces(
    marker_line_color="rgba(255,255,255,0.28)",
    marker_line_width=0.9,
    hovertemplate=(
        "<b>%{customdata[0]} (%{customdata[1]})</b><br>"
        "Indice démographique: %{customdata[2]:.3f}<extra></extra>"
    ),
)
fig_map.update_layout(
    template="plotly_dark",
    height=640,
    margin=dict(l=0, r=0, t=0, b=0),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font={"color": "#e8edf2"},
    coloraxis_colorbar={
        "title": {"text": demography_label_with_hint, "font": {"color": "#e8edf2"}},
        "tickfont": {"color": "#cfd6df"},
        "bgcolor": "rgba(0,0,0,0)",
        "len": 0.8,
        "thickness": 14,
        "outlinewidth": 0,
    },
    hoverlabel={
        "bgcolor": "#0f172a",
        "font_color": "#f8fafc",
        "bordercolor": "rgba(255,255,255,0.15)",
    },
)
st.plotly_chart(fig_map, use_container_width=True)
st.caption(
    "Lecture de la carte : plus l'indice est proche de 1, plus la structure d'âge du département reste jeune."
)

st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

st.subheader("Comprendre le phénomène")
metric_1, metric_2, metric_3 = st.columns(3)
metric_1.metric("Moyenne", f"{age_mean:.3f}")
metric_2.metric("Médiane", f"{age_median:.3f}")
metric_3.metric("Dispersion", f"{age_std:.3f}")
st.caption("Plus le score est proche de 1, plus le département est jeune.")

fig_hist = px.histogram(
    df,
    x="indice_vieillissement",
    nbins=18,
    color_discrete_sequence=["#b87333"],
    labels={"indice_vieillissement": demography_label_with_hint},
)
fig_hist.add_vline(
    x=age_mean,
    line_color="#38bdf8",
    line_width=2,
    line_dash="dash",
    annotation_text="Moyenne",
    annotation_position="top left",
)
fig_hist.add_vline(
    x=age_median,
    line_color="#e5e7eb",
    line_width=2,
    line_dash="dot",
    annotation_text="Médiane",
    annotation_position="top right",
)
fig_hist.update_layout(
    template="plotly_dark",
    height=380,
    margin=dict(l=20, r=20, t=20, b=20),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    bargap=0.08,
    showlegend=False,
)
fig_hist.update_traces(
    marker_line_color="rgba(255,255,255,0.15)",
    marker_line_width=1.0,
    hovertemplate="Indice: %{x:.3f}<br>Départements: %{y}<extra></extra>",
)
st.plotly_chart(fig_hist, use_container_width=True)
st.caption(
    "L'indice présente une forte hétérogénéité territoriale : certains départements restent jeunes, "
    "d'autres basculent vers une structure nettement plus âgée."
)

st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

st.subheader("Territoires gagnants / perdants")
col_young, col_old = st.columns(2)
with col_young:
    st.markdown("#### 🟢 Départements jeunes")
    st.dataframe(
        youngest_df[["Departement", "code", "indice_vieillissement"]].rename(
            columns={
                "Departement": "Département",
                "code": "Code",
                "indice_vieillissement": demography_label,
            }
        ),
        use_container_width=True,
        hide_index=True,
    )
with col_old:
    st.markdown("#### 🔴 Départements vieillissants")
    st.dataframe(
        oldest_df[["Departement", "code", "indice_vieillissement"]].rename(
            columns={
                "Departement": "Département",
                "code": "Code",
                "indice_vieillissement": demography_label,
            }
        ),
        use_container_width=True,
        hide_index=True,
    )
st.caption(
    "Une polarisation nette apparaît entre territoires attractifs et territoires en déclin démographique."
)

st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

st.subheader("Analyse stratégique")
st.caption("Croisement clé : indice démographique × confort thermique 2040.")
st.caption(
    "Confort thermique = 0.6 × nuits tropicales + 0.4 × jours > 35°C. "
    "Plus le score est proche de 1, plus la situation est favorable."
)

scatter_col, insight_col = st.columns([1.9, 1])
quadrant_colors = {
    "Double tension": "#b91c1c",
    "Jeunes mais exposés": "#f59e0b",
    "Vieillissants mais tempérés": "#94a3b8",
    "Profil plus favorable": "#22c55e",
}
fig_scatter = px.scatter(
    df,
    x="confort_thermique_2040",
    y="indice_vieillissement",
    color="profil_strategique",
    color_discrete_map=quadrant_colors,
    custom_data=["Departement", "code", "indice_vieillissement", "confort_thermique_2040"],
    labels={
        "confort_thermique_2040": "Confort thermique 2040 (1 = mieux)",
        "indice_vieillissement": demography_label_with_hint,
        "profil_strategique": "Profil",
    },
)
fig_scatter.update_traces(
    marker={"size": 10, "opacity": 0.86, "line": {"color": "rgba(255,255,255,0.28)", "width": 0.8}},
    hovertemplate=(
        "<b>%{customdata[0]} (%{customdata[1]})</b><br>"
        "Indice démographique: %{customdata[2]:.3f}<br>"
        "Confort thermique 2040: %{customdata[3]:.3f}<extra></extra>"
    ),
)
fig_scatter.add_vline(
    x=comfort_median,
    line_color="rgba(226,232,240,0.65)",
    line_dash="dash",
    line_width=1.6,
)
fig_scatter.add_hline(
    y=age_median,
    line_color="rgba(226,232,240,0.65)",
    line_dash="dash",
    line_width=1.6,
)
fig_scatter.add_vrect(
    x0=0,
    x1=comfort_median,
    fillcolor="rgba(185,28,28,0.10)",
    line_width=0,
    layer="below",
)
fig_scatter.add_hrect(
    y0=0,
    y1=age_median,
    fillcolor="rgba(185,28,28,0.06)",
    line_width=0,
    layer="below",
)
fig_scatter.update_layout(
    template="plotly_dark",
    height=560,
    margin=dict(l=20, r=20, t=20, b=20),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    legend={"orientation": "h", "y": 1.12, "x": 0.0, "title": None},
)

with scatter_col:
    st.plotly_chart(fig_scatter, use_container_width=True)

with insight_col:
    top_double = double_tension_df.sort_values("double_pression_score", ascending=False).head(3)
    top_double_text = ", ".join(top_double["Departement"].tolist()) if not top_double.empty else "Aucun cas net"
    st.markdown(
        f"""
<div class="story-card">
<div class="story-kicker">Lecture stratégique</div>
<div class="story-title">Le vrai risque est la superposition des fragilités</div>
<div class="story-body">
Les territoires les plus sensibles se lisent désormais en bas à gauche :
indice démographique faible et confort thermique faible.
</div>
<ul class="story-list">
<li><b>{double_tension_count}</b> départements sont dans le quadrant de double tension.</li>
<li>Le seuil médian sépare ici les départements plus jeunes des territoires déjà plus âgés, et les zones plus confortables des zones plus exposées.</li>
<li>Cas prioritaires à surveiller : <b>{top_double_text}</b>.</li>
</ul>
</div>
""",
        unsafe_allow_html=True,
    )

st.caption(
    "Lecture du scatter : la zone la plus critique est en bas à gauche, là où l'indice démographique "
    "est faible et le confort thermique aussi."
)

st.divider()
st.caption(
    "Sources mobilisées : INSEE pour la structure démographique, Météo-France / DRIAS pour les indicateurs thermiques 2040. "
    "Les indices sont normalisés sur une échelle 0-1."
)
