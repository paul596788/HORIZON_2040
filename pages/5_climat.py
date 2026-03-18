import json

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.excel_helpers import charger_csv, charger_geojson

st.set_page_config(page_title="Laboratoire climat 2040", layout="wide")

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
max-width: 1200px;
}
h1 {
font-weight: 700;
letter-spacing: -0.02em;
}
h2, h3 {
color: #e2e8f0;
font-weight: 600;
}
div[data-testid="stPlotlyChart"] {
background: rgba(255,255,255,0.01);
border: 1px solid rgba(255,255,255,0.06);
border-radius: 16px;
padding: 6px;
}
.metric-card {
background: rgba(255,255,255,0.03);
border: 1px solid rgba(255,255,255,0.08);
border-radius: 14px;
padding: 14px 16px;
}
.insight-card {
background: rgba(15,23,42,0.7);
border: 1px solid rgba(148,163,184,0.25);
border-radius: 14px;
padding: 12px 14px;
}
.insight-title {
font-weight: 700;
font-size: 1rem;
margin-bottom: 6px;
}
.insight-meta {
color: #cbd5e1;
font-size: 0.88rem;
margin-bottom: 8px;
}
.insight-list {
margin: 0.2rem 0 0.6rem 1rem;
padding: 0;
}
.insight-list li {
margin-bottom: 6px;
}
.section-spacer { height: 18px; }
</style>
""",
    unsafe_allow_html=True,
)

st.title("Analyse climatique 2040")
st.caption(
    "Évaluation des risques climatiques par département : interactions, corrélations et profils territoriaux."
)

# -----------------------------
# Load data
# -----------------------------
temperature_df = charger_csv("pages/tables/Temperature_2040_df.csv")
flood_df = charger_csv("pages/tables/Flood_df.csv")
water_df = charger_csv("pages/tables/water_pressure_df.csv")

# Base scores

temperature_df["score_temperature"] = (
    0.60 * temperature_df["nuits_tropicales"] + 0.40 * temperature_df["jours_sup_35C"]
)

flood_df["score_flood"] = (
    0.70 * flood_df["score_scena_risque_normalise"] + 0.30 * flood_df["score_land_perc"]
)

water_df["score_water"] = (
    0.40 * water_df["precipitations_ete"]
    + 0.30 * (1 - water_df["indice_humidite_sol"])
    + 0.20 * water_df["Volume"]
)

climate_df = (
    temperature_df[["code", "score_temperature"]]
    .merge(flood_df[["code", "score_flood"]], on="code", how="left")
    .merge(water_df[["code", "score_water"]], on="code", how="left")
)

# Handle potential missing values (align with main page defaults)
climate_df["score_flood"] = climate_df["score_flood"].fillna(1)
climate_df["score_water"] = climate_df["score_water"].fillna(0)
climate_df["score_temperature"] = climate_df["score_temperature"].fillna(0)

# Format codes
climate_df["code"] = climate_df["code"].astype(str).str.strip().str.upper()
climate_df["code"] = climate_df["code"].apply(
    lambda code: code.zfill(2) if code.isdigit() else code
)

# Demographic data (same as Explorer)
old_df = charger_csv("pages/tables/Old_df.csv")
old_df["code"] = old_df["code"].astype(str).str.strip().str.upper()
old_df["code"] = old_df["code"].apply(
    lambda code: code.zfill(2) if code.isdigit() else code
)
old_df = old_df[old_df["code"] != "M"]
old_df["score_vieillissement"] = pd.to_numeric(
    old_df["indice de vieillissement"], errors="coerce"
)

# Load geojson for names
departements = charger_geojson("pages/tables/departements.geojson")

code_to_nom = {
    feature["properties"]["code"]: feature["properties"]["nom"]
    for feature in departements.get("features", [])
}
climate_df["departement"] = climate_df["code"].map(code_to_nom).fillna(climate_df["code"])
climate_df["departement_label"] = climate_df["departement"] + " (" + climate_df["code"] + ")"

# Derived risk scores (1 = risque élevé)
climate_df["risque_temperature"] = 1 - climate_df["score_temperature"]
climate_df["risque_water"] = 1 - climate_df["score_water"]
climate_df["risque_flood"] = 1 - climate_df["score_flood"]

# -----------------------------
# Sidebar weights
# -----------------------------
st.sidebar.header("⚙️ Pondérations des risques")

defaults = {
    "w_climat": 0.7,
    "w_demo": 0.3,
    "w_temp": 0.6,
    "w_water": 0.3,
    "w_flood": 0.1,
}
for key, value in defaults.items():
    st.session_state.setdefault(key, value)

st.sidebar.subheader("Indice global (carte Explorer)")
st.sidebar.caption("Indice = 0.7 × Climat + 0.3 × Démographie")
w_climat = st.sidebar.slider("Poids climat", 0.0, 1.0, key="w_climat")
w_demo = st.sidebar.slider("Poids démographie", 0.0, 1.0, key="w_demo")

st.sidebar.divider()
st.sidebar.subheader("Décomposition du climat")
if st.sidebar.button("Preset climat (0.6 / 0.3 / 0.1)"):
    st.session_state["w_temp"] = 0.6
    st.session_state["w_water"] = 0.3
    st.session_state["w_flood"] = 0.1
w_temp = st.sidebar.slider("Poids température", 0.0, 1.0, key="w_temp")
w_water = st.sidebar.slider("Poids stress hydrique", 0.0, 1.0, key="w_water")
w_flood = st.sidebar.slider("Poids inondation", 0.0, 1.0, key="w_flood")

st.sidebar.caption(
    "Formule cible : Climat = 0.6 × Température + 0.1 × Inondation + 0.3 × Stress hydrique"
)

is_favorable = True
if is_favorable:
    temp_col = "score_temperature"
    water_col = "score_water"
    flood_col = "score_flood"
    temp_label = "Confort thermique"
    water_label = "Sécurité hydrique"
    flood_label = "Sécurité inondation"
    total_label = "Confort climatique"
    color_scale = "YlGn"
    mode_caption = "1 = meilleur (faible risque)"
else:
    temp_col = "risque_temperature"
    water_col = "risque_water"
    flood_col = "risque_flood"
    temp_label = "Risque thermique"
    water_label = "Risque hydrique"
    flood_label = "Risque d'inondation"
    total_label = "Risque total"
    color_scale = "YlOrRd"
    mode_caption = "1 = risque élevé"

label_map = {
    temp_col: temp_label,
    water_col: water_label,
    flood_col: flood_label,
}

poids_total = w_temp + w_water + w_flood
if poids_total == 0:
    st.warning("La somme des poids ne peut pas être nulle.")
    st.stop()

weighted_sum = (
    w_temp * climate_df[temp_col]
    + w_water * climate_df[water_col]
    + w_flood * climate_df[flood_col]
)
climate_df["indice_total"] = weighted_sum / poids_total

if is_favorable:
    climate_df["indice_resilience"] = climate_df["indice_total"]
else:
    climate_df["indice_resilience"] = 1 - climate_df["indice_total"]

# -----------------------------
# Carte rapide & cadran d'explication
# -----------------------------
st.subheader("Vue régionale et analyse contextuelle")

# Carte identique Explorer (indice global climat + démographie)
map_df = climate_df.merge(
    old_df[["code", "score_vieillissement"]], on="code", how="left"
)
map_df["score_vieillissement"] = map_df["score_vieillissement"].fillna(
    map_df["score_vieillissement"].mean()
)
map_df["indice_climat_map"] = (
    w_temp * map_df["score_temperature"]
    + w_water * map_df["score_water"]
    + w_flood * map_df["score_flood"]
) / poids_total
poids_global = w_climat + w_demo
if poids_global == 0:
    st.warning("La somme des poids de l'indice global ne peut pas être nulle.")
    map_df["indice_map"] = map_df["indice_climat_map"]
else:
    map_df["indice_map"] = (
        w_climat * map_df["indice_climat_map"]
        + w_demo * map_df["score_vieillissement"]
    ) / poids_global

color_scale_map = [
    (0.0, "#991b1b"),
    (0.2, "#c2410c"),
    (0.4, "#f59e0b"),
    (0.6, "#84cc16"),
    (0.8, "#22c55e"),
    (1.0, "#15803d"),
]

dept_options = (
    map_df[["code", "departement"]].drop_duplicates().sort_values("departement")
)
dept_codes = [""] + dept_options["code"].tolist()
dept_label_map = dict(zip(dept_options["code"], dept_options["departement"]))

selected_dept_code = st.selectbox(
    "Choisir un département (pour l'analyse)",
    options=dept_codes,
    index=0,
    format_func=lambda code: "Sélectionner un département..."
    if code == ""
    else f"{dept_label_map.get(code, code)} ({code})",
)

col_map, col_radar = st.columns(2)

radar_axes = [
    "Confort climatique",
    "Confort thermique",
    "Sécurité hydrique",
    "Sécurité inondation",
]
avg_values = [
    map_df["indice_map"].mean(),
    map_df["score_temperature"].mean(),
    map_df["score_water"].mean(),
    map_df["score_flood"].mean(),
]
dept_values = None
if selected_dept_code:
    dept_row = map_df[map_df["code"] == selected_dept_code].iloc[0]
    dept_values = [
        dept_row["indice_map"],
        dept_row["score_temperature"],
        dept_row["score_water"],
        dept_row["score_flood"],
    ]

axes_closed = radar_axes + [radar_axes[0]]

fig_radar = go.Figure()
if dept_values:
    fig_radar.add_trace(
        go.Scatterpolar(
            r=dept_values + [dept_values[0]],
            theta=axes_closed,
            name="Département",
            fill="toself",
            line={"color": "#38bdf8", "width": 2.6},
            marker={"size": 5, "color": "#38bdf8"},
            fillcolor="rgba(56,189,248,0.25)",
            hovertemplate="%{theta}: %{r:.2f}<extra></extra>",
        )
    )
fig_radar.add_trace(
    go.Scatterpolar(
        r=avg_values + [avg_values[0]],
        theta=axes_closed,
        name="Moyenne nationale",
        line={"color": "rgba(203,213,225,0.9)", "width": 2.2, "dash": "dash"},
        marker={"size": 5, "color": "rgba(203,213,225,0.9)"},
        hovertemplate="%{theta}: %{r:.2f}<extra></extra>",
    )
)
block_height = 320
fig_radar.update_layout(
    template="plotly_dark",
    height=block_height,
    margin=dict(l=48, r=48, t=60, b=32),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    legend={
        "orientation": "h",
        "y": 1.16,
        "x": 0.5,
        "xanchor": "center",
        "font": {"color": "#cbd5e1", "size": 12},
    },
    transition={"duration": 300, "easing": "cubic-in-out"},
    polar={
        "radialaxis": {
            "range": [0, 1],
            "tickvals": [0, 0.25, 0.5, 0.75, 1],
            "ticktext": ["0", "0.25", "0.5", "0.75", "1"],
            "tickfont": {"color": "#e2e8f0", "size": 12},
            "gridcolor": "rgba(148,163,184,0.4)",
            "linecolor": "rgba(148,163,184,0.4)",
            "showline": True,
        },
        "angularaxis": {
            "tickfont": {"color": "#f1f5f9", "size": 13},
            "gridcolor": "rgba(148,163,184,0.3)",
            "linecolor": "rgba(148,163,184,0.4)",
            "showline": True,
        },
        "bgcolor": "rgba(0,0,0,0)",
    },
)

mini_fig = px.choropleth(
    map_df,
    geojson=departements,
    locations="code",
    featureidkey="properties.code",
    color="indice_map",
    color_continuous_scale=color_scale_map,
)
mini_fig.update_geos(
    fitbounds="locations",
    visible=False,
    bgcolor="rgba(0,0,0,0)",
    projection={"type": "mercator"},
)
mini_fig.update_layout(
    template="plotly_dark",
    height=block_height,
    margin=dict(l=0, r=0, t=0, b=0),
    coloraxis_showscale=False,
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
)
mini_fig.update_traces(
    marker_line_color="rgba(255,255,255,0.35)",
    marker_line_width=0.8,
    hoverinfo="skip",
)

if selected_dept_code:
    mini_fig.add_trace(
        go.Choropleth(
            geojson=departements,
            locations=[selected_dept_code],
            featureidkey="properties.code",
            z=[1],
            colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(255,255,255,0.12)"]],
            showscale=False,
            marker_line_color="rgba(248,250,252,0.95)",
            marker_line_width=2.0,
            hoverinfo="skip",
            name="Sélection",
        )
    )

with col_map:
    st.plotly_chart(mini_fig, use_container_width=True, config={"displayModeBar": False})

with col_radar:
    st.plotly_chart(fig_radar, use_container_width=True, config={"displayModeBar": False})

if not selected_dept_code:
    st.caption("Sélectionne un département pour voir son profil radar.")

category_by_code = {
    "13": "multi",
    "30": "multi",
    "34": "multi",
    "83": "multi",
    "11": "multi",
    "33": "multi",
    "47": "multi",
    "25": "balanced",
    "39": "balanced",
    "73": "balanced",
    "74": "balanced",
    "59": "tradeoff",
    "86": "tradeoff",
    "44": "tradeoff",
    "49": "tradeoff",
    "85": "tradeoff",
    "90": "tradeoff",
    "66": "tradeoff",
    "69": "tradeoff",
    "28": "tradeoff",
    "84": "tradeoff",
}

category_text = {
    "multi": {
        "title": "Multi‑risques : convergence méditerranéenne & Sud‑Ouest",
        "meta": "Chaleur, stress hydrique et épisodes pluvieux intenses se renforcent mutuellement.",
        "bullets": [
            "Chaleur : forte insolation + anticyclone des Açores + urbanisation → îlots de chaleur urbains.",
            "Eau : ETP estivale > précipitations → déficit hydrique structurel, nappes peu tamponnées.",
            "Inondations : sols desséchés → ruissellement rapide lors d’épisodes orageux intenses.",
        ],
    },
    "balanced": {
        "title": "Départements équilibrés : effet “château d’eau” & inertie thermique",
        "meta": "Massifs, forêts et karsts jouent un rôle de régulation climatique et hydrique.",
        "bullets": [
            "Stockage naturel : massifs & karsts agissent comme réservoirs et soutiennent les débits.",
            "Confort thermique : altitude + couverture forestière → modération des extrêmes.",
            "Sécurité inondation : sols forestiers absorbants, densité plus faible en zones à risque.",
        ],
    },
    "tradeoff": {
        "title": "Trade‑offs & outliers : paradoxes géologiques et topographiques",
        "meta": "Un axe favorable peut masquer une vulnérabilité structurale.",
        "bullets": [
            "Socle granitique : faible infiltration → dépendance aux pluies annuelles.",
            "Relief plat/polders : évacuation lente → vulnérabilité aux pluies extrêmes.",
            "Cuvettes urbaines : minéralisation → surchauffe et ruissellement accrus.",
        ],
    },
}

dept_focus = {
    "13": "Mistral et épisodes méditerranéens : assèchement rapide puis crues éclairs.",
    "30": "Convergence Cévennes‑Méditerranée : orages stationnaires + sols secs.",
    "33": "Bassin aquitain : effet de cuvette + blocages anticycloniques persistants.",
    "47": "Sud‑Ouest : chaleur durable, nappes sollicitées en été.",
    "25": "Karsts jurassiens : stockage naturel et restitution progressive de l’eau.",
    "39": "Réseaux karstiques : régulation des débits, fraîcheur forestière.",
    "73": "Altitude et neige : inertie thermique, refroidissement nocturne des vallées.",
    "74": "Albédo neigeux + brises de pente : modération des canicules.",
    "59": "Relief très plat : évacuation lente, dépendance au système de pompage.",
    "86": "Seuil du Poitou : sous‑sol pauvre en stockage → fragilité hydrique.",
    "44": "Socle armoricain : nappes peu profondes, dépendance aux pluies annuelles.",
    "49": "Roches cristallines : faible capacité de stockage souterrain.",
    "85": "Insécurité hydrique structurelle malgré pluviométrie modérée.",
    "90": "Trouée de Belfort : nappes alluviales sensibles, territoire étroit.",
    "66": "Blocage pyrénéen : aridification progressive des sols.",
    "69": "Cuvette lyonnaise : minéralisation + chaleur urbaine.",
    "28": "Nappe de Beauce : forte sensibilité aux prélèvements.",
    "84": "Pressions agricoles + ETP élevée → stress hydrique marqué.",
}

if not selected_dept_code:
    st.caption("Sélectionne un département pour afficher l'analyse contextuelle.")
else:
    category = category_by_code.get(selected_dept_code, "tradeoff")
    card = category_text[category]
    focus = dept_focus.get(selected_dept_code)
    dept_name = dept_label_map.get(selected_dept_code, selected_dept_code)
    st.markdown(
        f"**{dept_name} ({selected_dept_code})**  \n{card['title']} — {card['meta']}"
    )
    with st.expander("Détails scientifiques", expanded=False):
        st.markdown(
            f"""
- {card['bullets'][0]}
- {card['bullets'][1]}
- {card['bullets'][2]}

**Focus local**
{focus if focus else "Pas de focus spécifique défini pour ce département."}
"""
        )

st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

vulnerability_df = pd.DataFrame(
    [
        {
            "Département": "Vaucluse (84)",
            "Facteur limitant principal": "Stress hydrique",
            "Cause scientifique": "Pressions agricoles + évapotranspiration élevée.",
        },
        {
            "Département": "Vienne (86)",
            "Facteur limitant principal": "Ressource en eau",
            "Cause scientifique": "Seuil du Poitou : zone de transition pauvre en stockage.",
        },
        {
            "Département": "Rhône (69)",
            "Facteur limitant principal": "Chaleur",
            "Cause scientifique": "Effet de cuvette lyonnaise + forte minéralisation.",
        },
        {
            "Département": "Eure-et-Loir (28)",
            "Facteur limitant principal": "Ressource en eau",
            "Cause scientifique": "Dépendance à la nappe de Beauce, sensible aux prélèvements.",
        },
    ]
)
with st.expander("📋 Tableau de synthèse des vulnérabilités spécifiques", expanded=False):
    st.dataframe(vulnerability_df, use_container_width=True, hide_index=True)
    st.download_button(
        "Exporter vers Sheets (CSV)",
        vulnerability_df.to_csv(index=False).encode("utf-8"),
        file_name="vulnerabilites_departements.csv",
        mime="text/csv",
    )

st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

# -----------------------------
# Risk interaction analysis
# -----------------------------
if is_favorable:
    st.subheader("Relations entre indicateurs climatiques")
else:
    st.subheader("Relations entre risques climatiques")
st.caption(
    "Chaque point représente un département. Survol pour détails complets. "
    f"Mode actuel : {mode_caption}."
)

hover_template = (
    "<b>%{customdata[0]}</b><br>"
    f"{temp_label}: %{{customdata[1]:.2f}}<br>"
    f"{water_label}: %{{customdata[2]:.2f}}<br>"
    f"{flood_label}: %{{customdata[3]:.2f}}<extra></extra>"
)

cluster_hover_template = (
    "<b>%{customdata[0]}</b><br>"
    f"{temp_label}: %{{customdata[1]:.2f}}<br>"
    f"{water_label}: %{{customdata[2]:.2f}}<br>"
    f"{flood_label}: %{{customdata[3]:.2f}}<br>"
    "Cluster: %{customdata[4]}<extra></extra>"
)

cols = st.columns(3)

scatter_specs = [
    (temp_col, water_col, temp_label, water_label),
    (temp_col, flood_col, temp_label, flood_label),
    (water_col, flood_col, water_label, flood_label),
]

for col, (x_col, y_col, x_label, y_label) in zip(cols, scatter_specs):
    fig = px.scatter(
        climate_df,
        x=x_col,
        y=y_col,
        color="indice_total",
        color_continuous_scale=color_scale,
        labels={x_col: x_label, y_col: y_label},
        custom_data=[
            "departement_label",
            temp_col,
            water_col,
            flood_col,
        ],
    )
    fig.update_traces(hovertemplate=hover_template, marker={"size": 7, "opacity": 0.85})
    fig.update_layout(
        template="plotly_dark",
        height=360,
        margin=dict(l=20, r=20, t=20, b=20),
        coloraxis_colorbar={"title": total_label},
    )
    with col:
        st.plotly_chart(fig, use_container_width=True)

st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

# -----------------------------
# Correlation matrix
# -----------------------------
st.subheader("Corrélations climatiques")

corr_df = climate_df[[temp_col, water_col, flood_col]].corr()
corr_df = corr_df.rename(index=label_map, columns=label_map)
fig_corr = px.imshow(
    corr_df,
    text_auto=".2f",
    color_continuous_scale="RdBu",
    zmin=-1,
    zmax=1,
    labels={"color": "Corrélation"},
)
fig_corr.update_layout(
    template="plotly_dark",
    height=420,
    margin=dict(l=20, r=20, t=40, b=20),
)
st.plotly_chart(fig_corr, use_container_width=True)

st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

# -----------------------------
# Insights rapides
# -----------------------------
st.subheader("Synthèse analytique")

axis_cols = [temp_col, water_col, flood_col]
axis_labels = {temp_col: temp_label, water_col: water_label, flood_col: flood_label}

insights_df = climate_df[
    ["departement", "code", "departement_label", "indice_total"] + axis_cols
].copy()
insights_df["axis_min"] = insights_df[axis_cols].min(axis=1)
insights_df["axis_max"] = insights_df[axis_cols].max(axis=1)
insights_df["axis_mean"] = insights_df[axis_cols].mean(axis=1)
insights_df["axis_std"] = insights_df[axis_cols].std(axis=1)
insights_df["balance_score"] = insights_df["axis_mean"] - 0.5 * insights_df["axis_std"]
insights_df["spread"] = insights_df["axis_max"] - insights_df["axis_min"]

if is_favorable:
    multi_title = "Top multi‑confort (haut sur les 3 axes)"
    balanced_title = "Top équilibrés (bons sur les 3 axes)"
    tradeoff_title = "Plus gros trade‑offs (forts écarts entre axes)"
    outlier_title = "Très bon score global mais point faible marqué"
else:
    multi_title = "Top multi‑risques (haut sur les 3 axes)"
    balanced_title = "Top équilibrés (risques élevés et homogènes)"
    tradeoff_title = "Plus gros trade‑offs (forts écarts entre axes)"
    outlier_title = "Bon score global mais risque extrême caché"

col_a, col_b = st.columns(2)

with col_a:
    st.caption(multi_title)
    st.dataframe(
        insights_df.sort_values("axis_min", ascending=False)
        .head(10)[["departement", "code", "indice_total"] + axis_cols]
        .rename(
            columns={
                "indice_total": total_label,
                temp_col: temp_label,
                water_col: water_label,
                flood_col: flood_label,
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

with col_b:
    st.caption(balanced_title)
    st.dataframe(
        insights_df.sort_values("balance_score", ascending=False)
        .head(10)[["departement", "code", "indice_total", "axis_std"] + axis_cols]
        .rename(
            columns={
                "indice_total": total_label,
                "axis_std": "Écart type (axes)",
                temp_col: temp_label,
                water_col: water_label,
                flood_col: flood_label,
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

col_c, col_d = st.columns(2)

with col_c:
    st.caption(tradeoff_title)
    tradeoffs = insights_df.copy()
    tradeoffs["Axe fort"] = tradeoffs[axis_cols].idxmax(axis=1).map(axis_labels)
    tradeoffs["Axe faible"] = tradeoffs[axis_cols].idxmin(axis=1).map(axis_labels)
    st.dataframe(
        tradeoffs.sort_values("spread", ascending=False)
        .head(10)[
            [
                "departement",
                "code",
                "Axe fort",
                "Axe faible",
                "spread",
                "indice_total",
            ]
        ]
        .rename(
            columns={
                "spread": "Écart max",
                "indice_total": total_label,
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

with col_d:
    st.caption(outlier_title)
    if is_favorable:
        overall_good = insights_df["indice_total"] >= insights_df["indice_total"].quantile(0.75)
        axis_bad = (insights_df[axis_cols] <= climate_df[axis_cols].quantile(0.2)).any(
            axis=1
        )
        outliers = insights_df[overall_good & axis_bad].copy()
        outliers["Axe critique"] = outliers[axis_cols].idxmin(axis=1).map(axis_labels)
        outliers["Score critique"] = outliers[axis_cols].min(axis=1)
        outliers = outliers.sort_values("Score critique", ascending=True)
    else:
        overall_good = insights_df["indice_total"] <= insights_df["indice_total"].quantile(0.25)
        axis_bad = (insights_df[axis_cols] >= climate_df[axis_cols].quantile(0.8)).any(
            axis=1
        )
        outliers = insights_df[overall_good & axis_bad].copy()
        outliers["Axe critique"] = outliers[axis_cols].idxmax(axis=1).map(axis_labels)
        outliers["Score critique"] = outliers[axis_cols].max(axis=1)
        outliers = outliers.sort_values("Score critique", ascending=False)

    if outliers.empty:
        st.info("Aucun cas net selon les seuils actuels.")
    else:
        st.dataframe(
            outliers.head(10)[
                ["departement", "code", "indice_total", "Axe critique", "Score critique"]
            ].rename(columns={"indice_total": total_label}),
            use_container_width=True,
            hide_index=True,
        )

st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

# -----------------------------
# Cumulative climate score
# -----------------------------
if is_favorable:
    st.subheader("Indice de confort climatique")
    st.caption("Top 10 des départements avec le confort climatique le plus élevé.")
else:
    st.subheader("Indice de risque climatique")
    st.caption("Top 10 des départements avec le risque climatique cumulé le plus élevé.")

top_total = climate_df.sort_values("indice_total", ascending=False).head(10)

st.dataframe(
    top_total[
        ["departement", "code", "indice_total", temp_col, water_col, flood_col]
    ].rename(
        columns={
            "indice_total": total_label,
            temp_col: temp_label,
            water_col: water_label,
            flood_col: flood_label,
        }
    ),
    use_container_width=True,
    hide_index=True,
)

st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

# -----------------------------
# Extreme territories
# -----------------------------
if is_favorable:
    st.subheader("Territoires favorables par indicateur")
else:
    st.subheader("Territoires vulnérables par indicateur")

col1, col2, col3 = st.columns(3)

with col1:
    st.caption(temp_label)
    st.dataframe(
        climate_df.sort_values(temp_col, ascending=False)
        .head(10)[["departement", "code", temp_col]]
        .rename(columns={temp_col: temp_label}),
        use_container_width=True,
        hide_index=True,
    )

with col2:
    st.caption(water_label)
    st.dataframe(
        climate_df.sort_values(water_col, ascending=False)
        .head(10)[["departement", "code", water_col]]
        .rename(columns={water_col: water_label}),
        use_container_width=True,
        hide_index=True,
    )

with col3:
    st.caption(flood_label)
    st.dataframe(
        climate_df.sort_values(flood_col, ascending=False)
        .head(10)[["departement", "code", flood_col]]
        .rename(columns={flood_col: flood_label}),
        use_container_width=True,
        hide_index=True,
    )

st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

# -----------------------------
# Climate resilience
# -----------------------------
st.subheader("Index de résilience climatique")

res_top = climate_df.sort_values("indice_resilience", ascending=False).head(10)

st.caption("Top 10 des départements les plus résilients au risque climatique.")
st.dataframe(
    res_top[["departement", "code", "indice_resilience"]].rename(
        columns={"indice_resilience": "Résilience"}
    ),
    use_container_width=True,
    hide_index=True,
)

st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

# -----------------------------
# Climate typology (clustering)
# -----------------------------
st.subheader("Typologies territoriales")

features = climate_df[[temp_col, water_col, flood_col]].copy()
features = features.fillna(features.mean())

cluster_notice = None
cluster_error = None
labels = None
cluster_name_map = {}

try:
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler

    X = StandardScaler().fit_transform(features)
    labels = KMeans(n_clusters=4, n_init=10, random_state=42).fit_predict(X)
except Exception:
    try:
        def _standardize(values: np.ndarray) -> np.ndarray:
            mean = np.nanmean(values, axis=0)
            std = np.nanstd(values, axis=0)
            std[std == 0] = 1.0
            return (values - mean) / std

        def _kmeans(
            values: np.ndarray,
            n_clusters: int,
            n_init: int,
            max_iter: int,
            random_state: int,
        ) -> np.ndarray:
            rng = np.random.default_rng(random_state)
            best_labels = None
            best_inertia = None

            for _ in range(n_init):
                if values.shape[0] >= n_clusters:
                    init_idx = rng.choice(values.shape[0], size=n_clusters, replace=False)
                else:
                    init_idx = rng.choice(values.shape[0], size=n_clusters, replace=True)
                centroids = values[init_idx]

                for _ in range(max_iter):
                    distances = np.sum(
                        (values[:, None, :] - centroids[None, :, :]) ** 2, axis=2
                    )
                    new_labels = np.argmin(distances, axis=1)
                    new_centroids = centroids.copy()
                    for k in range(n_clusters):
                        mask = new_labels == k
                        if not np.any(mask):
                            new_centroids[k] = values[rng.integers(0, values.shape[0])]
                        else:
                            new_centroids[k] = values[mask].mean(axis=0)
                    if np.allclose(new_centroids, centroids, atol=1e-6):
                        centroids = new_centroids
                        break
                    centroids = new_centroids

                inertia = np.sum((values - centroids[new_labels]) ** 2)
                if best_inertia is None or inertia < best_inertia:
                    best_inertia = inertia
                    best_labels = new_labels.copy()

            return best_labels

        X = _standardize(features.to_numpy(dtype=float))
        labels = _kmeans(X, n_clusters=4, n_init=10, max_iter=100, random_state=42)
        cluster_notice = "Clustering calculé sans scikit-learn (implémentation interne)."
    except Exception as exc:
        cluster_error = exc

if cluster_error or labels is None:
    detail = f"Détail: {cluster_error}" if cluster_error else "Détail: inconnu"
    st.warning(
        "Clustering indisponible (scikit-learn manquant ou erreur d'exécution). "
        f"{detail}"
    )
else:
    climate_df["cluster"] = labels.astype(int)
    if cluster_notice:
        st.info(cluster_notice)

    cluster_means = climate_df.groupby("cluster")[
        [temp_col, water_col, flood_col, "indice_total"]
    ].mean()
    cluster_sizes = climate_df["cluster"].value_counts()
    cluster_score = cluster_means["indice_total"]
    ordered_clusters = cluster_score.sort_values(ascending=False).index.tolist()
    letters = ["A", "B", "C", "D"]
    cluster_name_map = {
        cluster_id: f"Type {letters[i]}"
        for i, cluster_id in enumerate(ordered_clusters)
    }
    climate_df["cluster_name"] = climate_df["cluster"].map(cluster_name_map)

    quantiles = {
        temp_col: climate_df[temp_col].quantile([0.33, 0.66]).tolist(),
        water_col: climate_df[water_col].quantile([0.33, 0.66]).tolist(),
        flood_col: climate_df[flood_col].quantile([0.33, 0.66]).tolist(),
    }

    def _level(value: float, bounds: list[float]) -> str:
        low, high = bounds
        if value >= high:
            return "élevé"
        if value <= low:
            return "faible"
        return "moyen"

    profiles = {}
    for cluster_id, row in cluster_means.iterrows():
        profiles[cluster_id] = (
            f"{temp_label}: {_level(row[temp_col], quantiles[temp_col])} | "
            f"{water_label}: {_level(row[water_col], quantiles[water_col])} | "
            f"{flood_label}: {_level(row[flood_col], quantiles[flood_col])}"
        )

    cluster_summary = (
        cluster_means[[temp_col, water_col, flood_col, "indice_total"]]
        .assign(
            Type=lambda df: df.index.map(cluster_name_map),
            Profil=lambda df: df.index.map(profiles),
            Effectif=lambda df: df.index.map(cluster_sizes),
        )
        .reset_index(drop=True)
    )
    cluster_summary = cluster_summary[
        ["Type", "Profil", "Effectif", temp_col, water_col, flood_col, "indice_total"]
    ].rename(
        columns={
            temp_col: temp_label,
            water_col: water_label,
            flood_col: flood_label,
            "indice_total": total_label,
        }
    )

    centroids = cluster_means[[temp_col, water_col, flood_col]]
    example_rows = []
    for cluster_id in ordered_clusters:
        centroid = centroids.loc[cluster_id]
        subset = climate_df[climate_df["cluster"] == cluster_id].copy()
        distances = (
            (subset[[temp_col, water_col, flood_col]] - centroid) ** 2
        ).sum(axis=1)
        examples = (
            subset.assign(_dist=distances)
            .nsmallest(3, "_dist")["departement_label"]
            .tolist()
        )
        example_rows.append(
            {
                "Type": cluster_name_map[cluster_id],
                "Exemples": ", ".join(examples),
            }
        )
    examples_df = pd.DataFrame(example_rows)

    fig_cluster = px.scatter(
        climate_df,
        x=temp_col,
        y=water_col,
        color="cluster_name",
        color_discrete_sequence=["#22c55e", "#38bdf8", "#f97316", "#a855f7"],
        labels={temp_col: temp_label, water_col: water_label},
        custom_data=[
            "departement_label",
            temp_col,
            water_col,
            flood_col,
            "cluster_name",
        ],
        category_orders={
            "cluster_name": [cluster_name_map[c] for c in ordered_clusters]
        },
    )
    fig_cluster.update_traces(
        hovertemplate=cluster_hover_template, marker={"size": 7, "opacity": 0.9}
    )
    fig_cluster.update_layout(
        template="plotly_dark",
        height=420,
        margin=dict(l=20, r=20, t=20, b=20),
        legend_title_text="Cluster",
    )
    st.plotly_chart(fig_cluster, use_container_width=True)

    st.caption(
        f"Clusters basés sur {temp_label}, {water_label} et {flood_label}. "
        "Les types sont ordonnés du score global le plus élevé au plus faible."
    )
    st.dataframe(
        cluster_summary,
        use_container_width=True,
        hide_index=True,
    )
    st.caption("Exemples de départements proches des centres de cluster.")
    st.dataframe(
        examples_df,
        use_container_width=True,
        hide_index=True,
    )
######
