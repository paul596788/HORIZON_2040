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
    "Évaluation des risques climatiques par département : lecture cartographique, comparaison rapide et profils territoriaux."
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
    "w_temp": 0.6,
    "w_water": 0.3,
    "w_flood": 0.1,
}
for key, value in defaults.items():
    st.session_state.setdefault(key, value)

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

# -----------------------------
# Carte rapide & cadran d'explication
# -----------------------------
st.subheader("Vue régionale et analyse contextuelle")

# Carte climat uniquement
map_df = climate_df.copy()
map_df["indice_climat_map"] = (
    w_temp * map_df["score_temperature"]
    + w_water * map_df["score_water"]
    + w_flood * map_df["score_flood"]
) / poids_total
map_df["indice_map"] = map_df["indice_climat_map"]

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
dept_codes = dept_options["code"].tolist()
dept_label_map = dict(zip(dept_options["code"], dept_options["departement"]))

selected_dept_codes = st.multiselect(
    "Choisir un ou plusieurs départements (pour l'analyse)",
    options=dept_codes,
    format_func=lambda code: f"{dept_label_map.get(code, code)} ({code})",
    key="analysis_dept_codes",
    placeholder="Sélectionner un ou plusieurs départements...",
)
st.caption(
    "Le premier département sélectionné pilote les détails contextuels. "
    "Tous les départements sélectionnés sont comparés sur le radar, surlignés sur la carte "
    "et repris dans les analyses ci-dessous."
)

selected_dept_code = selected_dept_codes[0] if selected_dept_codes else ""
comparison_dept_codes = selected_dept_codes[1:] if len(selected_dept_codes) > 1 else []
has_selection = bool(selected_dept_codes)
selected_order_map = {code: idx for idx, code in enumerate(selected_dept_codes)}

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
axes_closed = radar_axes + [radar_axes[0]]

fig_radar = go.Figure()
radar_codes = [selected_dept_code] if selected_dept_code else []
radar_codes.extend(comparison_dept_codes)
radar_palette = ["#38bdf8", "#f59e0b", "#22c55e", "#f43f5e", "#a78bfa", "#06b6d4"]
selected_color_map = {
    code: radar_palette[idx % len(radar_palette)]
    for idx, code in enumerate(selected_dept_codes)
}

for idx, code in enumerate(radar_codes):
    dept_row = map_df[map_df["code"] == code].iloc[0]
    dept_values = [
        dept_row["indice_map"],
        dept_row["score_temperature"],
        dept_row["score_water"],
        dept_row["score_flood"],
    ]
    trace_name = f"{dept_label_map.get(code, code)} ({code})"
    trace_color = radar_palette[idx % len(radar_palette)]
    fig_radar.add_trace(
        go.Scatterpolar(
            r=dept_values + [dept_values[0]],
            theta=axes_closed,
            name=trace_name,
            fill="toself" if idx == 0 else None,
            line={"color": trace_color, "width": 2.6 if idx == 0 else 2.2},
            marker={"size": 5, "color": trace_color},
            fillcolor="rgba(56,189,248,0.22)" if idx == 0 else "rgba(0,0,0,0)",
            hovertemplate=f"<b>{trace_name}</b><br>%{{theta}}: %{{r:.2f}}<extra></extra>",
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
    custom_data=[
        "departement",
        "code",
        "indice_map",
        "score_temperature",
        "score_water",
        "score_flood",
    ],
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
    hovertemplate=(
        "<b>%{customdata[0]} (%{customdata[1]})</b><br>"
        "Indice climat: %{customdata[2]:.3f}<br>"
        "Confort thermique: %{customdata[3]:.3f}<br>"
        "Sécurité hydrique: %{customdata[4]:.3f}<br>"
        "Sécurité inondation: %{customdata[5]:.3f}<extra></extra>"
    ),
)

for idx, code in enumerate(selected_dept_codes):
    mini_fig.add_trace(
        go.Choropleth(
            geojson=departements,
            locations=[code],
            featureidkey="properties.code",
            z=[1],
            colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
            showscale=False,
            marker_line_color="rgba(255,255,255,0.98)",
            marker_line_width=3.0 if idx == 0 else 2.4,
            hoverinfo="skip",
            name=f"Sélection {idx + 1}",
            showlegend=False,
        )
    )

with col_map:
    st.plotly_chart(mini_fig, use_container_width=True, config={"displayModeBar": False})

with col_radar:
    st.plotly_chart(fig_radar, use_container_width=True, config={"displayModeBar": False})

if not selected_dept_code:
    st.caption("Sélectionne un ou plusieurs départements pour voir le radar.")
elif comparison_dept_codes:
    st.caption(
        "Le radar compare le département principal, les départements ajoutés et la moyenne nationale."
    )

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
    "01": (
        "🌦️ Climat : Semi-continental avec effet de vallée du Rhône → air chaud qui remonte vers les plaines  \n"
        "🌡️ Stress thermique : plaine de la Bresse fermée → air stagnant → accumulation de chaleur et nuits lourdes  \n"
        "💧 Stress hydrique : pluies correctes mais sols argilo-calcaires + maïs irrigué → forte consommation estivale → nappes sous tension  \n"
        "🌊 Inondations : crues de l’Ain et de la Saône → relief faible + sols saturés → débordements étendus  \n"
        "👴 Démographie : croissance périurbaine autour de Lyon → pression accrue sur l’eau  \n"
        "🧭 Lecture rapide : territoire piégé entre chaleur stagnante et agriculture gourmande en eau"
    ),
    "02": (
        "🌦️ Climat : Océanique dégradé, sans relief → systèmes pluvieux stagnants  \n"
        "🌡️ Stress thermique : faible ventilation + grandes plaines → chaleur diffuse mais persistante  \n"
        "💧 Stress hydrique : sols limoneux profonds → bonne rétention mais agriculture intensive → épuisement progressif en été  \n"
        "🌊 Inondations : nappes peu profondes + sols saturés l’hiver → remontées d’eau + crues lentes  \n"
        "👴 Démographie : territoires ruraux fragiles → faible capacité d’adaptation  \n"
        "🧭 Lecture rapide : un “château d’eau lent” qui déborde l’hiver et s’épuise l’été"
    ),
    "03": (
        "🌦️ Climat : Continental d’intérieur, loin des influences maritimes  \n"
        "🌡️ Stress thermique : bassin fermé → air chaud piégé → fortes amplitudes thermiques  \n"
        "💧 Stress hydrique : pluies irrégulières + sols peu épais sur socle granitique → faible stockage → sécheresse rapide  \n"
        "🌊 Inondations : orages estivaux → sols secs et imperméables → ruissellement brutal  \n"
        "👴 Démographie : population vieillissante → forte vulnérabilité aux canicules  \n"
        "🧭 Lecture rapide : territoire sans régulation naturelle, donc très sensible aux extrêmes"
    ),
    "04": (
        "🌦️ Climat : Méditerranéen montagnard, très ensoleillé → évaporation élevée  \n"
        "🌡️ Stress thermique : altitude moyenne mais air sec → forte montée en température en journée  \n"
        "💧 Stress hydrique : pluies rares + sols caillouteux → infiltration rapide → absence de stockage → pénurie structurelle  \n"
        "🌊 Inondations : torrents de montagne → pentes fortes + orages courts → crues violentes et localisées  \n"
        "👴 Démographie : faible densité mais isolement → accès aux ressources limité  \n"
        "🧭 Lecture rapide : l’eau ne reste jamais : soit elle manque, soit elle dévale"
    ),
    "05": (
        "🌦️ Climat : Montagnard sec, avec effet d’abri des Alpes → peu de précipitations  \n"
        "🌡️ Stress thermique : réchauffement rapide en altitude → étés plus chauds qu’avant  \n"
        "💧 Stress hydrique : dépendance à la neige → fonte précoce → décalage entre ressource et besoins estivaux  \n"
        "🌊 Inondations : fonte rapide + orages → torrents réactifs → crues soudaines  \n"
        "🧭 Lecture rapide : territoire dépendant d’un “réservoir neige” qui disparaît"
    ),
    "06": (
        "🌦️ Climat : Méditerranéen contraint par le relief → mer chaude + montagne proche  \n"
        "🌡️ Stress thermique : urbanisation littorale + relief qui bloque l’air → chaleur piégée et nuits très chaudes  \n"
        "💧 Stress hydrique : pluies concentrées en quelques épisodes + forte demande touristique → décalage entre ressource et usage → tension estivale  \n"
        "🌊 Inondations : épisodes méditerranéens → air chaud humide bloqué par les reliefs → pluies intenses → ruissellement explosif sur sols bétonnés  \n"
        "👴 Démographie : très forte densité côtière → exposition maximale  \n"
        "🧭 Lecture rapide : territoire où l’eau tombe violemment mais reste inutilisable"
    ),
    "07": (
        "🌦️ Climat : Méditerranéen intérieur, coupé de la mer par les Cévennes  \n"
        "🌡️ Stress thermique : vallées encaissées → chaleur stagnante → nuits tropicales fréquentes  \n"
        "💧 Stress hydrique : sols calcaires fissurés + pluies irrégulières → infiltration rapide → rivières à sec l’été  \n"
        "🌊 Inondations : épisodes cévenols → blocage des masses d’air → pluies diluviennes → crues éclairs  \n"
        "👴 Démographie : habitat dispersé et vieillissant → forte vulnérabilité  \n"
        "🧭 Lecture rapide : extrêmes hydriques : trop d’eau d’un coup, puis plus rien"
    ),
    "08": (
        "🌦️ Climat : Océanique frais sous influence continentale → humidité persistante  \n"
        "🌡️ Stress thermique : faible car couverture nuageuse fréquente → limitation des pics de chaleur  \n"
        "💧 Stress hydrique : pluies régulières + sols forestiers → bonne infiltration → faible stress global  \n"
        "🌊 Inondations : vallées encaissées + sols saturés → accumulation lente → crues durables  \n"
        "👴 Démographie : vieillissement et enclavement → vulnérabilité sociale  \n"
        "🧭 Lecture rapide : territoire humide et stable, mais sensible aux débordements prolongés"
    ),
    "09": (
        "🌦️ Climat : Montagnard avec influence méditerranéenne → contrastes forts  \n"
        "🌡️ Stress thermique : vallées abritées → chaleur piégée localement malgré altitude  \n"
        "💧 Stress hydrique : dépendance à la neige + baisse de l’enneigement → moins d’eau en été  \n"
        "🌊 Inondations : relief abrupt → orages + fonte → crues rapides et imprévisibles  \n"
        "👴 Démographie : faible densité et vieillissement → isolement face aux crises  \n"
        "🧭 Lecture rapide : un territoire “réservoir” qui se vide de plus en plus tôt"
    ),
    "10": (
        "🌦️ Climat : Semi-continental avec influence océanique atténuée  \n"
        "🌡️ Stress thermique : plaines ouvertes → forte exposition solaire → montée rapide des températures  \n"
        "💧 Stress hydrique : sols calcaires + cultures intensives → infiltration rapide mais prélèvements élevés → déficit estival  \n"
        "🌊 Inondations : grands bassins (Seine) + faible pente → crues lentes mais étendues  \n"
        "🧭 Lecture rapide : eau abondante mais mal synchronisée avec les besoins agricoles"
    ),
    "11": (
        "🌦️ Climat : Méditerranéen venté, couloir entre Atlantique et Méditerranée (effet tramontane)  \n"
        "🌡️ Stress thermique : vent asséchant + fort ensoleillement → montée rapide des températures et évaporation accrue  \n"
        "💧 Stress hydrique : pluies irrégulières + sols calcaires drainants + viticulture → faible stockage → sécheresse structurelle  \n"
        "🌊 Inondations : épisodes méditerranéens → air humide bloqué par les Corbières → pluies intenses → crues éclairs  \n"
        "🧭 Lecture rapide : territoire très ventilé où l’eau s’évapore vite et tombe violemment"
    ),
    "12": (
        "🌦️ Climat : Transition océanique / montagnard → fortes variations locales  \n"
        "🌡️ Stress thermique : plateaux exposés → fort rayonnement solaire → journées chaudes mais nuits encore fraîches  \n"
        "💧 Stress hydrique : sols calcaires fissurés (causses) → infiltration rapide → peu de réserves de surface  \n"
        "🌊 Inondations : relief marqué → ruissellement rapide lors d’orages → crues soudaines  \n"
        "👴 Démographie : population vieillissante en zones rurales  \n"
        "🧭 Lecture rapide : territoire “éponge percée” où l’eau disparaît sous terre"
    ),
    "13": (
        "🌦️ Climat : Méditerranéen sec, dominé par le mistral  \n"
        "🌡️ Stress thermique : vent chaud et sec + forte urbanisation → îlots de chaleur intenses  \n"
        "💧 Stress hydrique : très faibles pluies + forte demande (ville + industrie + agriculture) → dépendance aux apports extérieurs (Durance)  \n"
        "🌊 Inondations : pluies intenses sur sols secs et imperméabilisés → ruissellement rapide et crues urbaines  \n"
        "👴 Démographie : forte densité → exposition maximale  \n"
        "🧭 Lecture rapide : territoire artificialisé qui dépend d’eau importée pour fonctionner"
    ),
    "14": (
        "🌦️ Climat : Océanique humide sous influence directe de la Manche  \n"
        "🌡️ Stress thermique : faible car vents marins constants → limitation des fortes chaleurs  \n"
        "💧 Stress hydrique : pluies régulières + sols argileux → bonne rétention → faible tension estivale  \n"
        "🌊 Inondations : sols saturés + nappes superficielles → débordements fréquents et durables  \n"
        "👴 Démographie : littoral attractif → exposition accrue aux risques côtiers  \n"
        "🧭 Lecture rapide : territoire bien arrosé mais lent à évacuer l’eau"
    ),
    "15": (
        "🌦️ Climat : Montagnard humide, massif volcanique exposé aux flux atlantiques  \n"
        "🌡️ Stress thermique : modéré car altitude → limitation des extrêmes malgré le réchauffement  \n"
        "💧 Stress hydrique : bonne pluviométrie mais sols volcaniques drainants → stockage limité en surface  \n"
        "🌊 Inondations : relief + sols saturés → ruissellement rapide vers vallées → crues localisées  \n"
        "👴 Démographie : faible densité et vieillissement  \n"
        "🧭 Lecture rapide : château d’eau naturel, mais où l’eau circule vite sans rester"
    ),
    "16": (
        "🌦️ Climat : Océanique dégradé, moins influencé par la mer  \n"
        "🌡️ Stress thermique : intérieur des terres → chaleur qui stagne → épisodes plus longs  \n"
        "💧 Stress hydrique : sols calcaires + maïs irrigué → infiltration rapide mais forte consommation → nappes sous pression  \n"
        "🌊 Inondations : crues lentes (Charente) → faible pente → débordements étendus  \n"
        "🧭 Lecture rapide : eau qui circule mais peu stockée face à une forte demande agricole"
    ),
    "17": (
        "🌦️ Climat : Océanique avec influence marine directe  \n"
        "🌡️ Stress thermique : modéré mais zones urbaines littorales → chaleur piégée  \n"
        "💧 Stress hydrique : pluies modérées + sols sableux → faible rétention → déficit estival  \n"
        "🌊 Inondations : submersion + marais → montée des eaux + saturation → inondations durables  \n"
        "👴 Démographie : littoral attractif → forte exposition  \n"
        "🧭 Lecture rapide : territoire bas où l’eau de mer et douce s’accumulent"
    ),
    "18": (
        "🌦️ Climat : Continental atténué  \n"
        "🌡️ Stress thermique : étés chauds en plaine → chaleur persistante  \n"
        "💧 Stress hydrique : sols argilo-calcaires → stockage moyen mais agriculture → pression estivale  \n"
        "🌊 Inondations : crues lentes (Cher) → débordements larges  \n"
        "🧭 Lecture rapide : équilibre fragile entre stockage moyen et forte demande agricole"
    ),
    "19": (
        "🌦️ Climat : Océanique humide à relief marqué  \n"
        "🌡️ Stress thermique : modéré mais vallées → chaleur piégée localement  \n"
        "💧 Stress hydrique : pluies abondantes mais sols granitiques → faible rétention → sécheresse possible en été  \n"
        "🌊 Inondations : relief + pluies → ruissellement rapide → crues fréquentes  \n"
        "🧭 Lecture rapide : beaucoup d’eau… mais qui s’écoule trop vite"
    ),
    "2A": (
        "🌦️ Climat : Méditerranéen insulaire + relief montagneux proche du littoral → contrastes très forts sur peu de distance  \n"
        "🌡️ Stress thermique : plaines littorales encaissées + faible ventilation → chaleur piégée et nuits chaudes  \n"
        "💧 Stress hydrique : pluies concentrées en hiver + été très sec + forte pression touristique → demande maximale quand la ressource est minimale  \n"
        "🌊 Inondations : relief abrupt + orages méditerranéens → crues torrentielles très rapides  \n"
        "🧭 Lecture rapide : territoire à forte saisonnalité où l’eau manque précisément quand elle est la plus demandée"
    ),
    "2B": (
        "🌦️ Climat : Méditerranéen avec forte influence montagnarde → gradients très marqués entre côte et intérieur  \n"
        "🌡️ Stress thermique : plaines littorales (Bastia) → chaleur intense accentuée par l’humidité marine  \n"
        "💧 Stress hydrique : agriculture irriguée + faibles pluies estivales → tension élevée sur les ressources locales  \n"
        "🌊 Inondations : bassins versants courts (Golo, Tavignano) → réaction très rapide aux pluies intenses  \n"
        "🧭 Lecture rapide : territoire contrasté où les excès d’eau sont brutaux mais les pénuries fréquentes"
    ),
    "21": (
        "🌦️ Climat : Continental  \n"
        "🌡️ Stress thermique : vallées + vignobles → chaleur accumulée  \n"
        "💧 Stress hydrique : sols calcaires drainants → peu de stockage → tension pour la vigne  \n"
        "🌊 Inondations : crues modérées mais ruissellement local  \n"
        "🧭 Lecture rapide : terroir viticole très sensible au manque d’eau"
    ),
    "22": (
        "🌦️ Climat : Océanique humide  \n"
        "🌡️ Stress thermique : faible → influence maritime constante  \n"
        "💧 Stress hydrique : sols granitiques → faible stockage → sécheresse rapide malgré pluie  \n"
        "🌊 Inondations : ruissellement + saturation → crues fréquentes  \n"
        "🧭 Lecture rapide : humidité constante mais eau difficile à stocker"
    ),
    "23": (
        "🌦️ Climat : Océanique dégradé intérieur  \n"
        "🌡️ Stress thermique : hausse marquée → territoire peu ventilé  \n"
        "💧 Stress hydrique : sols granitiques + faible profondeur → faible réserve → sécheresse rapide  \n"
        "🌊 Inondations : ruissellement rapide sur sols saturés  \n"
        "👴 Démographie : très vieillissante  \n"
        "🧭 Lecture rapide : territoire pauvre en eau stockée et vulnérable"
    ),
    "24": (
        "🌦️ Climat : Océanique chaud  \n"
        "🌡️ Stress thermique : vallées → chaleur stagnante  \n"
        "💧 Stress hydrique : sols calcaires + irrigation → infiltration rapide → déficit  \n"
        "🌊 Inondations : crues larges (Dordogne)  \n"
        "🧭 Lecture rapide : eau abondante mais peu accessible en été"
    ),
    "25": (
        "🌦️ Climat : Montagnard continental  \n"
        "🌡️ Stress thermique : faible mais en hausse  \n"
        "💧 Stress hydrique : karst (calcaire fissuré) → eau disparaît sous terre → peu disponible  \n"
        "🌊 Inondations : crues rapides localisées  \n"
        "🧭 Lecture rapide : territoire où l’eau circule sous terre, peu exploitable"
    ),
    "26": (
        "🌦️ Climat : Transition méditerranéen / alpin, couloir du Rhône → vents fréquents  \n"
        "🌡️ Stress thermique : vallée du Rhône → air chaud canalisé → épisodes intenses et durables  \n"
        "💧 Stress hydrique : pluies irrégulières + sols caillouteux drainants + agriculture irriguée → faible stockage → tension estivale  \n"
        "🌊 Inondations : affluents du Rhône + orages → crues rapides  \n"
        "🧭 Lecture rapide : territoire ventilé mais structurellement sec en été"
    ),
    "27": (
        "🌦️ Climat : Océanique atténué, intérieur de la Normandie  \n"
        "🌡️ Stress thermique : modéré mais hausse progressive → plaines peu ventilées  \n"
        "💧 Stress hydrique : sols limoneux + nappes superficielles → bonne réserve mais forte agriculture → tension locale  \n"
        "🌊 Inondations : nappes proches + sols saturés → inondations lentes et durables  \n"
        "🧭 Lecture rapide : territoire où l’eau s’accumule lentement mais peut manquer en été"
    ),
    "28": (
        "🌦️ Climat : Continental de plaine (Beauce)  \n"
        "🌡️ Stress thermique : grande plaine ouverte → fort ensoleillement → chaleur intense  \n"
        "💧 Stress hydrique : sols calcaires + agriculture céréalière intensive → prélèvements massifs → baisse des nappes  \n"
        "🌊 Inondations : faible pente → stagnation de l’eau → crues diffuses  \n"
        "🧭 Lecture rapide : “grenier agricole” très dépendant d’une nappe surexploitée"
    ),
    "29": (
        "🌦️ Climat : Océanique pur, exposé aux vents atlantiques  \n"
        "🌡️ Stress thermique : très faible → régulation permanente par la mer  \n"
        "💧 Stress hydrique : pluies abondantes mais sols granitiques peu profonds → faible stockage → sécheresse rapide dès arrêt des pluies  \n"
        "🌊 Inondations : pluies continues + ruissellement → crues fréquentes mais modérées  \n"
        "🧭 Lecture rapide : beaucoup d’eau, mais qui ne tient pas dans les sols"
    ),
    "30": (
        "🌦️ Climat : Méditerranéen avec influence cévenole  \n"
        "🌡️ Stress thermique : plaines chaudes + ensoleillement → fortes canicules  \n"
        "💧 Stress hydrique : été très sec + sols calcaires drainants → faible réserve → pénurie estivale  \n"
        "🌊 Inondations : épisodes cévenols → blocage des masses d’air → pluies extrêmes → crues éclairs  \n"
        "🧭 Lecture rapide : territoire d’extrêmes : sec l’été, violent à l’automne"
    ),
    "31": (
        "🌦️ Climat : Transition océanique / méditerranéen  \n"
        "🌡️ Stress thermique : urbanisation de Toulouse + faible vent → îlot de chaleur marqué  \n"
        "💧 Stress hydrique : dépendance à la Garonne + irrigation → tension en période sèche  \n"
        "🌊 Inondations : Garonne + orages → crues rapides  \n"
        "👴 Démographie : forte croissance → pression accrue  \n"
        "🧭 Lecture rapide : métropole en croissance qui tire sur une ressource fluviale variable"
    ),
    "32": (
        "🌦️ Climat : Océanique chaud à influence méditerranéenne  \n"
        "🌡️ Stress thermique : collines exposées → forte chaleur estivale  \n"
        "💧 Stress hydrique : sols argilo-calcaires + agriculture (maïs) → forte demande → tension estivale  \n"
        "🌊 Inondations : orages + sols imperméables → ruissellement rapide  \n"
        "🧭 Lecture rapide : territoire agricole très dépendant de l’eau en été"
    ),
    "33": (
        "🌦️ Climat : Océanique tempéré, littoral + estuaire  \n"
        "🌡️ Stress thermique : modéré mais zones urbaines (Bordeaux) → chaleur amplifiée  \n"
        "💧 Stress hydrique : sols sableux → infiltration rapide → nappes vulnérables + forte demande  \n"
        "🌊 Inondations : estuaire de la Gironde → crues + submersion + remontée saline  \n"
        "🧭 Lecture rapide : territoire où l’eau circule vite et remonte depuis la mer"
    ),
    "34": (
        "🌦️ Climat : Méditerranéen sec  \n"
        "🌡️ Stress thermique : ensoleillement intense → chaleur forte et durable  \n"
        "💧 Stress hydrique : très faibles pluies + urbanisation + tourisme → forte pression → pénurie fréquente  \n"
        "🌊 Inondations : épisodes méditerranéens → pluies violentes sur sols secs → ruissellement massif  \n"
        "🧭 Lecture rapide : territoire structurellement sec avec des pluies destructrices"
    ),
    "35": (
        "🌦️ Climat : Océanique tempéré  \n"
        "🌡️ Stress thermique : modéré mais hausse en zones urbaines  \n"
        "💧 Stress hydrique : sols limoneux peu profonds → stockage limité → tension estivale croissante  \n"
        "🌊 Inondations : saturation hivernale + ruissellement → crues fréquentes  \n"
        "🧭 Lecture rapide : territoire intermédiaire qui bascule vers plus d’extrêmes"
    ),
    "36": (
        "🌦️ Climat : Continental atténué  \n"
        "🌡️ Stress thermique : étés chauds en plaine → chaleur persistante  \n"
        "💧 Stress hydrique : sols argilo-calcaires + agriculture → demande élevée → déficit estival  \n"
        "🌊 Inondations : crues lentes → accumulation d’eau  \n"
        "🧭 Lecture rapide : territoire agricole exposé à la sécheresse progressive"
    ),
    "37": (
        "🌦️ Climat : Océanique dégradé  \n"
        "🌡️ Stress thermique : vallée de la Loire → chaleur piégée  \n"
        "💧 Stress hydrique : sols calcaires + viticulture → infiltration rapide → tension estivale  \n"
        "🌊 Inondations : Loire → crues larges mais lentes  \n"
        "🧭 Lecture rapide : eau abondante mais mal retenue pour l’été"
    ),
    "38": (
        "🌦️ Climat : Montagnard + vallées fermées  \n"
        "🌡️ Stress thermique : effet cuvette (Grenoble) → chaleur piégée → nuits très chaudes  \n"
        "💧 Stress hydrique : dépendance neige + fonte précoce → déficit en fin d’été  \n"
        "🌊 Inondations : torrents alpins → crues rapides  \n"
        "🧭 Lecture rapide : chaleur extrême en vallée malgré un territoire de montagne"
    ),
    "39": (
        "🌦️ Climat : Montagnard humide  \n"
        "🌡️ Stress thermique : modéré  \n"
        "💧 Stress hydrique : karst calcaire → infiltration profonde → eau peu disponible en surface  \n"
        "🌊 Inondations : crues rapides localisées  \n"
        "🧭 Lecture rapide : territoire où l’eau disparaît sous terre"
    ),
    "40": (
        "🌦️ Climat : Océanique sableux  \n"
        "🌡️ Stress thermique : chaleur modérée mais sécheresse accentuée par sols sableux  \n"
        "💧 Stress hydrique : sols très perméables → infiltration rapide → faible rétention → sécheresse + incendies  \n"
        "🌊 Inondations : nappes hautes en hiver → zones humides saturées  \n"
        "🧭 Lecture rapide : territoire qui sèche vite et brûle facilement"
    ),
    "41": (
        "🌦️ Climat : Transition océanique / continental  \n"
        "🌡️ Stress thermique : hausse en plaine  \n"
        "💧 Stress hydrique : sols mixtes + agriculture → tension modérée  \n"
        "🌊 Inondations : Loire + Cher → crues étendues  \n"
        "🧭 Lecture rapide : alternance marquée entre excès et manque d’eau"
    ),
    "42": (
        "🌦️ Climat : Continental avec influence montagnarde  \n"
        "🌡️ Stress thermique : bassins industriels → chaleur piégée  \n"
        "💧 Stress hydrique : ressources variables + usage industriel → tension locale  \n"
        "🌊 Inondations : relief + pluies → crues rapides  \n"
        "🧭 Lecture rapide : territoire contrasté entre industrie et montagne"
    ),
    "43": (
        "🌦️ Climat : Montagnard volcanique  \n"
        "🌡️ Stress thermique : modéré  \n"
        "💧 Stress hydrique : dépendance aux pluies → peu de nappes → sensibilité aux sécheresses  \n"
        "🌊 Inondations : ruissellement rapide sur relief  \n"
        "🧭 Lecture rapide : territoire dépendant directement des précipitations"
    ),
    "44": (
        "🌦️ Climat : Océanique + estuaire  \n"
        "🌡️ Stress thermique : modéré  \n"
        "💧 Stress hydrique : sols humides mais salinisation possible → pression sur ressource  \n"
        "🌊 Inondations : estuaire + submersion + marais → inondations étendues  \n"
        "🧭 Lecture rapide : territoire bas soumis à l’eau venant de la mer et du fleuve"
    ),
    "45": (
        "🌦️ Climat : Continental atténué  \n"
        "🌡️ Stress thermique : hausse en plaine  \n"
        "💧 Stress hydrique : nappe de Beauce très exploitée → baisse des niveaux  \n"
        "🌊 Inondations : Loire → crues larges  \n"
        "🧭 Lecture rapide : dépendance critique à une nappe surexploitée"
    ),
    "46": (
        "🌦️ Climat : Méditerranéen intérieur  \n"
        "🌡️ Stress thermique : chaleur forte en été  \n"
        "💧 Stress hydrique : sols calcaires karstiques → eau infiltrée → peu disponible  \n"
        "🌊 Inondations : crues rapides en vallée  \n"
        "🧭 Lecture rapide : eau invisible car stockée en profondeur"
    ),
    "47": (
        "🌦️ Climat : Océanique chaud  \n"
        "🌡️ Stress thermique : étés chauds  \n"
        "💧 Stress hydrique : irrigation intensive → forte pression sur ressources  \n"
        "🌊 Inondations : Garonne → crues  \n"
        "🧭 Lecture rapide : agriculture très dépendante de l’eau"
    ),
    "48": (
        "🌦️ Climat : Montagnard cévenol  \n"
        "🌡️ Stress thermique : modéré  \n"
        "💧 Stress hydrique : pluies importantes mais ruissellement rapide → peu de stockage  \n"
        "🌊 Inondations : épisodes cévenols → crues brutales  \n"
        "🧭 Lecture rapide : château d’eau… qui ne retient pas l’eau"
    ),
    "49": (
        "🌦️ Climat : Océanique doux  \n"
        "🌡️ Stress thermique : modéré  \n"
        "💧 Stress hydrique : agriculture + sols drainants → tension estivale  \n"
        "🌊 Inondations : Loire → crues étendues  \n"
        "🧭 Lecture rapide : territoire entre abondance hivernale et manque estival"
    ),
    "50": (
        "🌦️ Climat : Océanique très humide  \n"
        "🌡️ Stress thermique : faible  \n"
        "💧 Stress hydrique : pluies abondantes → faible stress  \n"
        "🌊 Inondations : sols saturés + nappes hautes → débordements fréquents  \n"
        "🧭 Lecture rapide : territoire humide mais saturé"
    ),
    "51": (
        "🌦️ Climat : Continental sec de plaine → peu de relief donc peu de blocage des masses d’air  \n"
        "🌡️ Stress thermique : plaines ouvertes → fort ensoleillement → chaleur rapide  \n"
        "💧 Stress hydrique : sols crayeux → infiltration rapide → eau peu disponible en surface l’été  \n"
        "🌊 Inondations : nappes + vallées larges → crues lentes et étendues  \n"
        "🧭 Lecture rapide : eau stockée en profondeur mais peu accessible en surface"
    ),
    "52": (
        "🌦️ Climat : Continental de plateau → contrastes marqués  \n"
        "🌡️ Stress thermique : modéré mais en hausse → territoire intérieur sensible aux canicules  \n"
        "💧 Stress hydrique : sols calcaires + plateaux → infiltration rapide → rivières en baisse l’été  \n"
        "🌊 Inondations : têtes de bassin → réactions rapides puis débordements en aval  \n"
        "🧭 Lecture rapide : territoire source d’eau qui se vide rapidement en été"
    ),
    "53": (
        "🌦️ Climat : Océanique doux mais intérieur → influence maritime atténuée  \n"
        "🌡️ Stress thermique : modéré mais plus durable dans les zones peu ventilées  \n"
        "💧 Stress hydrique : sols peu profonds → stockage limité → sécheresse plus rapide qu’attendu  \n"
        "🌊 Inondations : sols saturés + rivières lentes → crues progressives  \n"
        "🧭 Lecture rapide : territoire humide en apparence mais peu résilient"
    ),
    "54": (
        "🌦️ Climat : Continental avec vallées marquées  \n"
        "🌡️ Stress thermique : vallées → chaleur piégée → nuits chaudes  \n"
        "💧 Stress hydrique : ressources globales correctes mais pression locale → tensions estivales  \n"
        "🌊 Inondations : confluences + urbanisation → débordements aggravés  \n"
        "🧭 Lecture rapide : territoire où relief et usages concentrent les risques"
    ),
    "55": (
        "🌦️ Climat : Continental humide et ouvert  \n"
        "🌡️ Stress thermique : modéré mais en hausse → éloignement maritime  \n"
        "💧 Stress hydrique : pluies régulières mais sécheresses plus longues → baisse des débits  \n"
        "🌊 Inondations : vallée large et plate → crues lentes mais durables  \n"
        "🧭 Lecture rapide : territoire lent, entre excès hivernal et manque estival"
    ),
    "56": (
        "🌦️ Climat : Océanique doux, très influencé par l’océan  \n"
        "🌡️ Stress thermique : faible car vents marins → limitation des extrêmes  \n"
        "💧 Stress hydrique : sols granitiques + îles → faible stockage → tensions estivales locales  \n"
        "🌊 Inondations : zones basses + marais → submersion + saturation  \n"
        "🧭 Lecture rapide : eau omniprésente mais fragile à stocker sur le littoral"
    ),
    "57": (
        "🌦️ Climat : Continental avec influences humides  \n"
        "🌡️ Stress thermique : vallées industrielles → chaleur piégée + îlots urbains  \n"
        "💧 Stress hydrique : pluies correctes mais forte consommation industrielle → pression locale  \n"
        "🌊 Inondations : vallées encaissées → accumulation → crues marquées  \n"
        "🧭 Lecture rapide : territoire industriel où l’eau est disponible mais très sollicitée"
    ),
    "58": (
        "🌦️ Climat : Océanique dégradé intérieur  \n"
        "🌡️ Stress thermique : étés plus chauds → territoire peu ventilé  \n"
        "💧 Stress hydrique : sols mixtes + faible densité → stress modéré mais en hausse  \n"
        "🌊 Inondations : Loire + affluents → crues étendues  \n"
        "🧭 Lecture rapide : territoire de transition qui bascule vers plus de sécheresse"
    ),
    "59": (
        "🌦️ Climat : Océanique humide et peu ensoleillé  \n"
        "🌡️ Stress thermique : faible mais zones urbaines → chaleur accumulée  \n"
        "💧 Stress hydrique : pluies régulières mais sols artificialisés → faible infiltration → tensions locales  \n"
        "🌊 Inondations : ruissellement urbain + nappes hautes → inondations fréquentes  \n"
        "👴 Démographie : très dense → forte exposition  \n"
        "🧭 Lecture rapide : beaucoup d’eau mais mal absorbée par les sols urbanisés"
    ),
    "60": (
        "🌦️ Climat : Océanique dégradé proche bassin parisien  \n"
        "🌡️ Stress thermique : périurbanisation → îlots de chaleur diffus  \n"
        "💧 Stress hydrique : nappes sollicitées (Paris) → pression structurelle  \n"
        "🌊 Inondations : crues lentes + sols saturés  \n"
        "🧭 Lecture rapide : territoire sous influence parisienne qui tire sur ses ressources"
    ),
    "61": (
        "🌦️ Climat : Océanique humide  \n"
        "🌡️ Stress thermique : faible → régulation océanique  \n"
        "💧 Stress hydrique : sols argileux → bonne rétention → faible stress  \n"
        "🌊 Inondations : saturation hivernale → crues lentes  \n"
        "🧭 Lecture rapide : territoire stable mais lent à évacuer l’eau"
    ),
    "62": (
        "🌦️ Climat : Océanique venté  \n"
        "🌡️ Stress thermique : faible → vents constants  \n"
        "💧 Stress hydrique : nappes importantes mais pollution + urbanisation → disponibilité réduite  \n"
        "🌊 Inondations : nappes affleurantes + relief faible → submersions fréquentes  \n"
        "🧭 Lecture rapide : eau présente mais difficilement mobilisable"
    ),
    "63": (
        "🌦️ Climat : Montagnard intérieur volcanique  \n"
        "🌡️ Stress thermique : contrastes forts → plaines chaudes, sommets frais  \n"
        "💧 Stress hydrique : sols volcaniques drainants → infiltration rapide → peu de stockage  \n"
        "🌊 Inondations : ruissellement rapide sur pentes  \n"
        "🧭 Lecture rapide : territoire perméable où l’eau disparaît rapidement"
    ),
    "64": (
        "🌦️ Climat : Océanique très humide + montagne  \n"
        "🌡️ Stress thermique : faible → influence océan + altitude  \n"
        "💧 Stress hydrique : abondant mais relief → écoulement rapide vers mer  \n"
        "🌊 Inondations : pluies + pentes → crues fréquentes  \n"
        "🧭 Lecture rapide : beaucoup d’eau mais difficile à retenir"
    ),
    "65": (
        "🌦️ Climat : Montagnard humide  \n"
        "🌡️ Stress thermique : faible mais en hausse  \n"
        "💧 Stress hydrique : dépendance neige → fonte précoce → manque estival  \n"
        "🌊 Inondations : torrents + fonte → crues rapides  \n"
        "🧭 Lecture rapide : ressource dépendante d’un manteau neigeux en recul"
    ),
    "66": (
        "🌦️ Climat : Méditerranéen sec + effet de foehn  \n"
        "🌡️ Stress thermique : air sec descendant → chaleur amplifiée  \n"
        "💧 Stress hydrique : très faible pluie + agriculture → pénurie chronique  \n"
        "🌊 Inondations : épisodes méditerranéens violents mais rares  \n"
        "🧭 Lecture rapide : territoire parmi les plus secs de France"
    ),
    "67": (
        "🌦️ Climat : Continental abrité par les Vosges  \n"
        "🌡️ Stress thermique : effet de plaine fermée → chaleur stagnante  \n"
        "💧 Stress hydrique : pluies faibles (ombre des Vosges) → déficit structurel  \n"
        "🌊 Inondations : Rhin + affluents → crues contrôlées mais possibles  \n"
        "🧭 Lecture rapide : zone sèche cachée derrière un massif montagneux"
    ),
    "68": (
        "🌦️ Climat : Continental sec (record de sécheresse en France)  \n"
        "🌡️ Stress thermique : fort en plaine d’Alsace → chaleur intense  \n"
        "💧 Stress hydrique : très faible pluie + sols drainants → stress élevé  \n"
        "🌊 Inondations : Rhin → risque maîtrisé mais présent  \n"
        "🧭 Lecture rapide : une des zones les plus sèches malgré l’image du nord-est"
    ),
    "69": (
        "🌦️ Climat : Transition continental / méditerranéen  \n"
        "🌡️ Stress thermique : vallée encaissée + urbanisation (Lyon) → îlot de chaleur majeur  \n"
        "💧 Stress hydrique : forte demande urbaine + agricole → tension sur Rhône et nappes  \n"
        "🌊 Inondations : Rhône + ruissellement urbain  \n"
        "🧭 Lecture rapide : territoire sous pression combinée climat + métropole"
    ),
    "70": (
        "🌦️ Climat : Continental humide  \n"
        "🌡️ Stress thermique : modéré  \n"
        "💧 Stress hydrique : sols argileux → bonne rétention → faible stress  \n"
        "🌊 Inondations : saturation → crues lentes  \n"
        "🧭 Lecture rapide : territoire humide mais vulnérable aux débordements"
    ),
    "71": (
        "🌦️ Climat : Continental atténué, entre vallées et bocages → contrastes marqués entre plaines chaudes et reliefs plus humides  \n"
        "🌡️ Stress thermique : vallées de la Saône et secteurs urbanisés → chaleur qui stagne → épisodes plus lourds en été  \n"
        "💧 Stress hydrique : sols argilo-calcaires + élevage et cultures → réserve moyenne mais forte demande estivale → tension locale  \n"
        "🌊 Inondations : Saône lente + affluents réactifs → débordements étendus en plaine  \n"
        "🧭 Lecture rapide : territoire d’équilibre fragile, entre stockage moyen et forte variabilité selon les vallées"
    ),
    "72": (
        "🌦️ Climat : Océanique dégradé → humidité régulière mais influence marine affaiblie dans l’intérieur  \n"
        "🌡️ Stress thermique : plaines et villes moyennes → chaleur plus durable lors des épisodes longs  \n"
        "💧 Stress hydrique : sols peu profonds sur socle ancien + agriculture → réserves limitées → assecs plus fréquents en été  \n"
        "🌊 Inondations : rivières lentes + sols saturés en hiver → crues progressives  \n"
        "🧭 Lecture rapide : territoire encore tempéré, mais de plus en plus sensible au manque d’eau estival"
    ),
    "73": (
        "🌦️ Climat : Alpin → forte dépendance au relief, à la neige et aux vallées  \n"
        "🌡️ Stress thermique : vallées encaissées → chaleur piégée → nuits chaudes malgré l’image de fraîcheur montagnarde  \n"
        "💧 Stress hydrique : ressource abondante mais très saisonnière → fonte plus précoce → moins d’eau disponible en fin d’été  \n"
        "🌊 Inondations : torrents + fonte + orages → crues rapides et localisées  \n"
        "🧭 Lecture rapide : montagne riche en eau, mais de plus en plus décalée entre recharge printanière et besoins estivaux"
    ),
    "74": (
        "🌦️ Climat : Alpin humide → relief très marqué et forte influence de la neige  \n"
        "🌡️ Stress thermique : bassins urbanisés et vallées → chaleur piégée localement → hausse nette des nuits chaudes  \n"
        "💧 Stress hydrique : dépendance à la neige et aux glaciers + forte croissance résidentielle et touristique → tension croissante en été  \n"
        "🌊 Inondations : torrents alpins + urbanisation en fond de vallée → débordements rapides  \n"
        "🧭 Lecture rapide : territoire de montagne sous pression, où la ressource reste forte mais plus difficile à synchroniser avec les usages"
    ),
    "75": (
        "🌦️ Climat : Océanique dégradé très urbanisé → le bâti domine largement le fonctionnement local  \n"
        "🌡️ Stress thermique : minéralisation massive + faible végétation → îlot de chaleur très fort → nuits particulièrement chaudes  \n"
        "💧 Stress hydrique : dépendance à des ressources importées + forte consommation urbaine → vulnérabilité en cas d’étiage régional  \n"
        "🌊 Inondations : Seine lente + imperméabilisation → crue fluviale aggravée par ruissellement urbain  \n"
        "🧭 Lecture rapide : territoire où le risque vient moins du climat brut que de l’intensité urbaine"
    ),
    "76": (
        "🌦️ Climat : Océanique humide, exposé à la Manche → vents fréquents et humidité élevée  \n"
        "🌡️ Stress thermique : limité sur le littoral, mais plus marqué dans les vallées industrielles et urbaines  \n"
        "💧 Stress hydrique : pluies régulières mais sols de plateau crayeux → infiltration profonde → tensions locales possibles en été  \n"
        "🌊 Inondations : ruissellement sur plateaux, vallées encaissées et submersion littorale → risques multiples  \n"
        "🧭 Lecture rapide : eau présente mais répartie de façon inégale entre plateaux secs et vallées très exposées"
    ),
    "77": (
        "🌦️ Climat : Continental de plaine, ouvert et peu ventilé  \n"
        "🌡️ Stress thermique : grandes surfaces agricoles + périurbanisation → forte exposition solaire → chaleur intense  \n"
        "💧 Stress hydrique : nappes de Beauce et cultures intensives → prélèvements élevés → tension croissante en été  \n"
        "🌊 Inondations : vallées larges (Seine, Marne) + urbanisation diffuse → crues lentes mais étendues  \n"
        "🧭 Lecture rapide : grand territoire productif qui dépend fortement de nappes déjà très sollicitées"
    ),
    "78": (
        "🌦️ Climat : Océanique dégradé sous influence parisienne  \n"
        "🌡️ Stress thermique : urbanisation + vallées boisées localement peu ventilées → chaleur plus durable  \n"
        "💧 Stress hydrique : nappes et rivières sous pression métropolitaine → ressource disponible mais très demandée  \n"
        "🌊 Inondations : Seine + ruissellement périurbain → débordements accentués par l’imperméabilisation  \n"
        "🧭 Lecture rapide : territoire de transition, où la pression urbaine transforme des risques modérés en tensions réelles"
    ),
    "79": (
        "🌦️ Climat : Océanique atténué, plus sec dans l’intérieur  \n"
        "🌡️ Stress thermique : plaines agricoles ouvertes → chaleur rapide en été  \n"
        "💧 Stress hydrique : faibles réserves naturelles + irrigation importante → forte tension sur nappes et cours d’eau  \n"
        "🌊 Inondations : sols localement imperméables + pluies orageuses → ruissellement rapide  \n"
        "🧭 Lecture rapide : territoire agricole où le vrai point dur est la concurrence pour une ressource limitée"
    ),
    "80": (
        "🌦️ Climat : Océanique frais, peu contrasté mais très humide  \n"
        "🌡️ Stress thermique : faible à modéré, surtout dans les pôles urbains  \n"
        "💧 Stress hydrique : ressource globalement correcte, mais sols calcaires et craie → eau surtout stockée en profondeur  \n"
        "🌊 Inondations : nappes affleurantes + vallée très plate → inondations lentes, longues et diffuses  \n"
        "🧭 Lecture rapide : territoire de nappes, où l’eau monte d’en bas plus qu’elle ne déborde brutalement"
    ),
    "81": (
        "🌦️ Climat : Transition océanique / méditerranéen → contrastes forts entre ouest plus humide et est plus sec  \n"
        "🌡️ Stress thermique : vallées et plaines intérieures → chaleur qui s’installe durablement  \n"
        "💧 Stress hydrique : été sec + agriculture + sols souvent peu profonds → tension croissante sur rivières et retenues  \n"
        "🌊 Inondations : orages sur reliefs et vallées → crues rapides localisées  \n"
        "🧭 Lecture rapide : territoire charnière où la bascule vers un fonctionnement plus méditerranéen devient visible"
    ),
    "82": (
        "🌦️ Climat : Océanique chaud à influence méditerranéenne  \n"
        "🌡️ Stress thermique : plaine ouverte + fort ensoleillement → canicules fréquentes  \n"
        "💧 Stress hydrique : arboriculture, maïs et irrigation → forte demande estivale → pression sur cours d’eau et nappes  \n"
        "🌊 Inondations : Garonne, Tarn et orages → crues rapides ou débordements étendus selon les secteurs  \n"
        "🧭 Lecture rapide : territoire productif très dépendant d’une eau de plus en plus disputée l’été"
    ),
    "83": (
        "🌦️ Climat : Méditerranéen sec, très ensoleillé, avec reliefs proches du littoral  \n"
        "🌡️ Stress thermique : urbanisation littorale + étés secs → chaleur forte et nuits de moins en moins fraîches  \n"
        "💧 Stress hydrique : pluies concentrées hors été + forte demande résidentielle et touristique → pénurie estivale récurrente  \n"
        "🌊 Inondations : épisodes méditerranéens + sols secs ou artificialisés → ruissellement brutal  \n"
        "🧭 Lecture rapide : territoire typique du paradoxe méditerranéen : manque d’eau chronique, excès d’eau soudain"
    ),
    "84": (
        "🌦️ Climat : Méditerranéen intérieur, très ensoleillé, marqué par le mistral  \n"
        "🌡️ Stress thermique : plaines du Comtat et vallée du Rhône → chaleur amplifiée par l’air sec  \n"
        "💧 Stress hydrique : été sec + agriculture irriguée + sols drainants → forte dépendance aux apports extérieurs, notamment Durance  \n"
        "🌊 Inondations : crues de l’Ouvèze, du Rhône et ruissellement orageux → risques contrastés mais marqués  \n"
        "🧭 Lecture rapide : territoire chaud et agricole, structurellement dépendant d’une eau transférée"
    ),
    "85": (
        "🌦️ Climat : Océanique doux, littoral bas et intérieur plus sec  \n"
        "🌡️ Stress thermique : modéré mais plus marqué dans les zones urbanisées et rétro-littorales  \n"
        "💧 Stress hydrique : faibles reliefs + sols variables + forte pression estivale sur le littoral → réserves limitées en été  \n"
        "🌊 Inondations : submersion marine, marais et ruissellement → accumulation d’eau dans les secteurs bas  \n"
        "🧭 Lecture rapide : territoire basculant entre manque d’eau d’été et vulnérabilité forte aux eaux côtières"
    ),
    "86": (
        "🌦️ Climat : Océanique dégradé, plus chaud et sec que le littoral atlantique  \n"
        "🌡️ Stress thermique : plaines ouvertes → montée rapide des températures estivales  \n"
        "💧 Stress hydrique : sols calcaires + agriculture céréalière → infiltration rapide et forte demande → tension sur nappes  \n"
        "🌊 Inondations : vallées de la Vienne et du Clain → crues lentes, localement aggravées par le ruissellement  \n"
        "🧭 Lecture rapide : territoire de plaine où la chaleur progresse vite et où l’eau de surface devient plus fragile"
    ),
    "87": (
        "🌦️ Climat : Océanique dégradé sur socle granitique  \n"
        "🌡️ Stress thermique : modéré mais en hausse dans les bassins et zones urbaines  \n"
        "💧 Stress hydrique : sols granitiques peu profonds → faible stockage → baisse rapide des débits en été  \n"
        "🌊 Inondations : pluies répétées + ruissellement sur sols vite saturés → crues fréquentes mais souvent localisées  \n"
        "🧭 Lecture rapide : territoire où l’eau paraît présente, mais reste peu retenue par les sols"
    ),
    "88": (
        "🌦️ Climat : Montagnard humide, très influencé par le relief  \n"
        "🌡️ Stress thermique : limité sur les hauteurs, mais vallées plus exposées aux chaleurs durables  \n"
        "💧 Stress hydrique : bonne pluviométrie mais ressource très liée aux forêts, tourbières et débits de montagne → sensibilité aux sécheresses longues  \n"
        "🌊 Inondations : pentes, vallées étroites et pluies abondantes → crues rapides  \n"
        "🧭 Lecture rapide : massif encore humide, mais dont les fonctions de stockage naturel deviennent plus fragiles"
    ),
    "89": (
        "🌦️ Climat : Continental atténué, assez sec pour le nord de la Bourgogne  \n"
        "🌡️ Stress thermique : plaines et vallées → chaleur persistante en été  \n"
        "💧 Stress hydrique : sols calcaires + vigne et grandes cultures → infiltration rapide → tension estivale  \n"
        "🌊 Inondations : Yonne et affluents → crues lentes, parfois renforcées par ruissellement local  \n"
        "🧭 Lecture rapide : territoire agricole et viticole où l’eau manque surtout quand les besoins montent"
    ),
    "90": (
        "🌦️ Climat : Continental humide, ouvert par la trouée de Belfort → circulation d’air marquée  \n"
        "🌡️ Stress thermique : modéré mais en hausse dans les zones urbanisées de fond de vallée  \n"
        "💧 Stress hydrique : ressource correcte mais très dépendante des pluies régionales → sensibilité accrue en été  \n"
        "🌊 Inondations : petits bassins versants + relief → crues rapides après fortes pluies  \n"
        "🧭 Lecture rapide : petit territoire de passage où les cours d’eau réagissent très vite aux épisodes intenses"
    ),
    "91": (
        "🌦️ Climat : Océanique dégradé sous forte influence francilienne  \n"
        "🌡️ Stress thermique : urbanisation diffuse + surfaces minérales → chaleur durable et nuits plus chaudes  \n"
        "💧 Stress hydrique : nappes et cours d’eau sollicités par la métropole → pression structurelle sur la ressource  \n"
        "🌊 Inondations : vallées de l’Essonne, de l’Orge et imperméabilisation → ruissellement et débordements  \n"
        "🧭 Lecture rapide : territoire où la pression urbaine transforme des ressources ordinaires en point de fragilité"
    ),
    "92": (
        "🌦️ Climat : Urbain dense, fortement modifié par le bâti  \n"
        "🌡️ Stress thermique : minéralisation extrême + très faible rafraîchissement nocturne → îlot de chaleur très fort  \n"
        "💧 Stress hydrique : dépendance quasi totale à des ressources externes + forte consommation → vulnérabilité indirecte  \n"
        "🌊 Inondations : Seine + ruissellement urbain rapide → forte exposition des infrastructures  \n"
        "🧭 Lecture rapide : département où l’artificialisation domine largement le risque climatique"
    ),
    "93": (
        "🌦️ Climat : Urbain dense, peu végétalisé, sous influence métropolitaine  \n"
        "🌡️ Stress thermique : bâti serré + manque d’ombre → surchauffe rapide et forte vulnérabilité nocturne  \n"
        "💧 Stress hydrique : ressource importée mais forte sensibilité aux restrictions et aux inégalités d’accès au confort  \n"
        "🌊 Inondations : ruissellement urbain + secteurs en vallée → débordements localisés mais impacts élevés  \n"
        "🧭 Lecture rapide : territoire où la vulnérabilité vient surtout de la densité urbaine et du manque de sols absorbants"
    ),
    "94": (
        "🌦️ Climat : Océanique dégradé très urbanisé, structuré par les vallées de la Seine et de la Marne  \n"
        "🌡️ Stress thermique : densité bâtie + vallées peu ventilées → chaleur piégée  \n"
        "💧 Stress hydrique : ressource disponible via grands réseaux, mais forte dépendance à une gestion extérieure  \n"
        "🌊 Inondations : confluence Seine-Marne + urbanisation ancienne en zone basse → risque fluvial majeur  \n"
        "🧭 Lecture rapide : territoire très exposé car la ville s’est installée au contact direct des grandes rivières"
    ),
    "95": (
        "🌦️ Climat : Océanique dégradé, entre plateaux agricoles et vallées urbanisées  \n"
        "🌡️ Stress thermique : chaleur marquée dans les secteurs urbanisés et fonds de vallée  \n"
        "💧 Stress hydrique : nappes sollicitées + agriculture de plateau → tensions locales en été  \n"
        "🌊 Inondations : Oise, Seine et ruissellement périurbain → risques combinés  \n"
        "🧭 Lecture rapide : territoire hybride, où s’additionnent pression métropolitaine, agriculture et vallées exposées"
    ),
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
**Focus local**
{focus if focus else "Pas de focus spécifique défini pour ce département."}
"""
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
    base_marker = {"size": 7, "opacity": 0.3 if has_selection else 0.85}
    fig.update_traces(hovertemplate=hover_template, marker=base_marker)

    if has_selection:
        for code in selected_dept_codes:
            selected_row = climate_df[climate_df["code"] == code]
            if selected_row.empty:
                continue
            fig.add_trace(
                go.Scatter(
                    x=selected_row[x_col],
                    y=selected_row[y_col],
                    mode="markers",
                    name=selected_row["departement_label"].iloc[0],
                    showlegend=False,
                    customdata=selected_row[
                        ["departement_label", temp_col, water_col, flood_col]
                    ].to_numpy(),
                    hovertemplate=hover_template,
                    marker={
                        "size": 12,
                        "color": selected_color_map.get(code, "#f8fafc"),
                        "line": {"color": "#ffffff", "width": 2},
                    },
                )
            )

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
insights_df["spread"] = insights_df["axis_max"] - insights_df["axis_min"]

tradeoffs = insights_df.copy()
tradeoffs["Axe fort"] = tradeoffs[axis_cols].idxmax(axis=1).map(axis_labels)
tradeoffs["Axe faible"] = tradeoffs[axis_cols].idxmin(axis=1).map(axis_labels)
if has_selection:
    tradeoffs_view = tradeoffs[tradeoffs["code"].isin(selected_dept_codes)].copy()
    tradeoffs_view["selection_order"] = tradeoffs_view["code"].map(selected_order_map)
    tradeoffs_view = tradeoffs_view.sort_values("selection_order").drop(
        columns="selection_order"
    )
    st.caption("Lecture des départements sélectionnés : axe fort, axe faible et écart entre axes.")
else:
    tradeoffs_view = tradeoffs.sort_values("spread", ascending=False).head(10)
    st.caption("Départements avec les écarts les plus marqués entre axes climatiques.")

st.dataframe(
    tradeoffs_view[
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

st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

# -----------------------------
# Cumulative climate score
# -----------------------------
st.subheader("Classement synthétique")

top_total = (
    climate_df.sort_values("indice_total", ascending=False)
    [["departement", "code", "indice_total"]]
    .reset_index(drop=True)
)
top_total.insert(0, "Rang", range(1, len(top_total) + 1))

if has_selection:
    ranking_view = top_total[top_total["code"].isin(selected_dept_codes)].copy()
    ranking_view["selection_order"] = ranking_view["code"].map(selected_order_map)
    ranking_view = ranking_view.sort_values("selection_order").drop(columns="selection_order")
    st.caption("Position des départements sélectionnés dans le classement national.")
else:
    ranking_view = top_total.head(10)
    st.caption("Top 10 des départements les mieux classés sur l'indice climatique global.")

st.dataframe(
    ranking_view.rename(columns={"indice_total": total_label}),
    use_container_width=True,
    hide_index=True,
)

st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

# -----------------------------
# Climate typology (clustering)
# -----------------------------
with st.expander("Analyse avancée : typologies territoriales", expanded=False):
    st.caption(
        "Vue analyste : segmentation des départements selon les trois axes climatiques. "
        "Sortie volontairement séparée du flux principal."
    )

    features = climate_df[[temp_col, water_col, flood_col]].copy()
    features = features.fillna(features.mean())

    cluster_notice = None
    cluster_error = None
    labels = None

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
        cluster_df = climate_df.copy()
        cluster_df["cluster"] = labels.astype(int)
        if cluster_notice:
            st.info(cluster_notice)

        cluster_means = cluster_df.groupby("cluster")[
            [temp_col, water_col, flood_col, "indice_total"]
        ].mean()
        cluster_sizes = cluster_df["cluster"].value_counts()
        ordered_clusters = cluster_means["indice_total"].sort_values(ascending=False).index.tolist()
        letters = ["A", "B", "C", "D"]
        cluster_name_map = {
            cluster_id: f"Type {letters[i]}"
            for i, cluster_id in enumerate(ordered_clusters)
        }
        cluster_df["cluster_name"] = cluster_df["cluster"].map(cluster_name_map)

        quantiles = {
            temp_col: cluster_df[temp_col].quantile([0.33, 0.66]).tolist(),
            water_col: cluster_df[water_col].quantile([0.33, 0.66]).tolist(),
            flood_col: cluster_df[flood_col].quantile([0.33, 0.66]).tolist(),
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
            subset = cluster_df[cluster_df["cluster"] == cluster_id].copy()
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

        fig_cluster = px.scatter_3d(
            cluster_df,
            x=temp_col,
            y=water_col,
            z=flood_col,
            color="cluster_name",
            color_discrete_sequence=["#22c55e", "#38bdf8", "#f97316", "#a855f7"],
            labels={
                temp_col: temp_label,
                water_col: water_label,
                flood_col: flood_label,
            },
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
            hovertemplate=cluster_hover_template,
            marker={"size": 5, "opacity": 0.18 if has_selection else 0.85},
        )

        if has_selection:
            for code in selected_dept_codes:
                selected_row = cluster_df[cluster_df["code"] == code]
                if selected_row.empty:
                    continue
                fig_cluster.add_trace(
                    go.Scatter3d(
                        x=selected_row[temp_col],
                        y=selected_row[water_col],
                        z=selected_row[flood_col],
                        mode="markers",
                        name=selected_row["departement_label"].iloc[0],
                        showlegend=False,
                        customdata=selected_row[
                            [
                                "departement_label",
                                temp_col,
                                water_col,
                                flood_col,
                                "cluster_name",
                            ]
                        ].to_numpy(),
                        hovertemplate=cluster_hover_template,
                        marker={
                            "size": 8,
                            "color": selected_color_map.get(code, "#f8fafc"),
                            "line": {"color": "#ffffff", "width": 3},
                            "opacity": 1,
                        },
                    )
                )

        fig_cluster.update_layout(
            template="plotly_dark",
            height=560,
            margin=dict(l=20, r=20, t=20, b=20),
            legend_title_text="Cluster",
            scene={
                "xaxis_title": temp_label,
                "yaxis_title": water_label,
                "zaxis_title": flood_label,
            },
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

        if has_selection:
            selected_cluster_view = cluster_df[
                cluster_df["code"].isin(selected_dept_codes)
            ].copy()
            selected_cluster_view["selection_order"] = selected_cluster_view["code"].map(
                selected_order_map
            )
            selected_cluster_view = selected_cluster_view.sort_values("selection_order")
            st.caption("Positionnement cluster des départements sélectionnés.")
            st.dataframe(
                selected_cluster_view[
                    [
                        "departement",
                        "code",
                        "cluster_name",
                        temp_col,
                        water_col,
                        flood_col,
                        "indice_total",
                    ]
                ].rename(
                    columns={
                        "cluster_name": "Type",
                        temp_col: temp_label,
                        water_col: water_label,
                        flood_col: flood_label,
                        "indice_total": total_label,
                    }
                ),
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
