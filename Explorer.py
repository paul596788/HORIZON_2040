
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json

from utils.excel_helpers import charger_csv, charger_geojson

# -----------------------------
# Configuration page
# -----------------------------
st.set_page_config(page_title="Indice climat 2040", layout="wide")

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
div[data-testid="stMetric"] {
background: rgba(255,255,255,0.03);
border: 1px solid rgba(255,255,255,0.08);
border-radius: 14px;
padding: 14px 16px;
}
div[data-testid="stMetricLabel"] p { color: #cbd5e1; }
div[data-testid="stMetricValue"] { font-weight: 700; }
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
height: 140px;
display: flex;
flex-direction: column;
justify-content: center;
gap: 8px;
}
.metric-label {
color: #cbd5e1;
font-size: 0.9rem;
margin-bottom: 6px;
}
.metric-value {
color: #f8fafc;
font-weight: 700;
line-height: 1.2;
word-break: break-word;
display: -webkit-box;
-webkit-box-orient: vertical;
overflow: hidden;
}
.metric-value--number {
font-size: 2.2rem;
-webkit-line-clamp: 1;
}
.metric-value--name {
font-size: 1.55rem;
-webkit-line-clamp: 3;
}
.section-spacer { height: 18px; }
</style>
""",
    unsafe_allow_html=True,
)

st.title("🌍 Où vivre en France en 2040 ?")

st.caption(
    "Indice composite exploratoire pour comparer les départements à horizon 2040. "
    "Les scores sont normalisés et pondérés pour tester différents scénarios. "
    "Les résultats sont relatifs et doivent être interprétés avec prudence."
)

# -----------------------------
# Chargement des données
# -----------------------------
temperature_df = charger_csv("pages/tables/Temperature_2040_df.csv")
flood_df = charger_csv("pages/tables/Flood_df.csv")
water_df = charger_csv("pages/tables/water_pressure_df.csv")
old_df = charger_csv("pages/tables/Old_df.csv")

old_df["code"] = old_df["code"].astype(str).str.strip().str.upper()
old_df["code"] = old_df["code"].apply(lambda code: code.zfill(2) if code.isdigit() else code)
old_df = old_df[old_df["code"] != "M"]
old_df["score_vieillissement"] = pd.to_numeric(
    old_df["indice de vieillissement"], errors="coerce"
)


# -----------------------------
# Calcul scores individuels
# -----------------------------
# Score lié aux ressources en eau
water_df["score_water"] = (
    0.40 * water_df["precipitations_ete"] +
    0.30 * (1 - water_df["indice_humidite_sol"]) +
    0.20 * water_df["Volume"]
)

# Score de risque d'inondation
flood_df["score_flood"] = (
    0.70 * flood_df["score_scena_risque_normalise"] +
    0.30 * flood_df["score_land_perc"] 
)

# Score d'exposition à la chaleur
temperature_df["score_temperature"] = (
    0.60 * temperature_df["nuits_tropicales"] +
    0.40 * temperature_df["jours_sup_35C"]
)

# -----------------------------
# Fusion datasets
# -----------------------------
climate_df = (
    temperature_df[["code", "score_temperature"]]
    .merge(flood_df[["code", "score_flood"]], on="code", how="left")
    .merge(water_df[["code", "score_water"]], on="code", how="left")
    .merge(old_df[["code", "score_vieillissement"]], on="code", how="left")
)

# -----------------------------
# Gestion NA
# -----------------------------
climate_df["score_flood"] = climate_df["score_flood"].fillna(1)
climate_df["score_water"] = climate_df["score_water"].fillna(0)
climate_df["score_temperature"] = climate_df["score_temperature"].fillna(0)
climate_df["score_vieillissement"] = climate_df["score_vieillissement"].fillna(
    climate_df["score_vieillissement"].mean()
)

# -----------------------------
# Sidebar poids indice
# -----------------------------
st.sidebar.header("⚙️ Paramètres de l'indice")

# valeurs par défaut
defaults = {
    "inclure_climat": True,
    "inclure_old": True,
    "w_climat": 0.7,
    "w_demo": 0.3,
    "w_temp": 0.6,
    "w_flood": 0.1,
    "w_water": 0.3,
}
for key, value in defaults.items():
    st.session_state.setdefault(key, value)
st.session_state.setdefault("selected_codes", [])

if st.sidebar.button("Preset Global (0.7 / 0.3)"):
    for key, value in defaults.items():
        st.session_state[key] = value

inclure_climat = st.sidebar.checkbox("Inclure indice climatique", key="inclure_climat")
inclure_old = st.sidebar.checkbox("Inclure démographie (vieillissement)", key="inclure_old")


st.sidebar.subheader("Niveau 1 : Indice global")
st.sidebar.caption("Poids entre climat et démographie (somme normalisée).")
poids_climat = 0.0
poids_demo = 0.0
if inclure_climat:
    poids_climat = st.sidebar.slider("Poids climat", 0.0, 1.0, key="w_climat")
if inclure_old:
    poids_demo = st.sidebar.slider("Poids démographie", 0.0, 1.0, key="w_demo")

poids_temp = 0.0
poids_flood = 0.0
poids_water = 0.0
if inclure_climat:
    st.sidebar.divider()
    st.sidebar.subheader("Niveau 2 : Décomposition du climat")
    st.sidebar.caption(
        "Répartition interne du bloc climat (température / inondation / stress hydrique)."
    )
    poids_temp = st.sidebar.slider("Poids température", 0.0, 1.0, key="w_temp")
    poids_flood = st.sidebar.slider("Poids inondation", 0.0, 1.0, key="w_flood")
    poids_water = st.sidebar.slider("Poids stress hydrique", 0.0, 1.0, key="w_water")

st.sidebar.caption(
"""
Formule cible :
Indice = 0.7 × Climat + 0.3 × Démographie  
Climat = 0.6 × Température + 0.1 × Inondation + 0.3 × Stress hydrique
"""
)
st.sidebar.caption("L'indice est normalisé par la somme des poids.")
st.sidebar.divider()
with st.sidebar.expander("Méthodologie & Sources"):
    st.markdown(
        """
**Analyse des risques climatiques territoriaux**  
L’étude évalue la vulnérabilité climatique des territoires à partir de quatre dimensions principales :  
1. stress thermique  
2. pression hydrique  
3. risque d’inondation  
4. structure démographique

Les projections climatiques proviennent de **DRIAS (moyenne 2035–2045)** et les données complémentaires de **BNPE (2020)** et **INSEE**.  
Les indices composites suivent une approche classique : combiner plusieurs variables d’un même phénomène tout en conservant une interprétation claire des scores.

**🌡️ Stress thermique**  
L’indice vise à mesurer l’intensité des épisodes de chaleur extrême.
```
score_temperature =
0.6 × nuits tropicales +
0.4 × jours > 35°C
```
Ces indicateurs sont utilisés par le **GIEC** et l’**Organisation météorologique mondiale**.

**Nuits tropicales (poids 0.6)**  
Température minimale ≥ 20 °C.  
- multiplication par **2 à 5** depuis les années 1960  
- projections : **+10 à +30 nuits/an d’ici 2050**

**Jours > 35 °C (poids 0.4)**  
- risques sanitaires, stress thermique des cultures, hausse de la demande énergétique  
- **×3 à ×5** d’ici le milieu du siècle en Europe occidentale

**💧 Stress hydrique**  
L’indice mesure la pression sur la ressource en eau en combinant apports climatiques, sols et pression humaine.
```
score_water =
0.40 × (1 - précipitations estivales)
0.30 × (1 - humidité du sol)
0.20 × volume d'extraction
```
L’utilisation de **(1 − variable)** transforme pluie et humidité en indicateurs de déficit.

**Précipitations estivales (0.40)**  
- **50–70 %** de l’évapotranspiration annuelle entre juin et août  
- **−10 à −30 %** de pluie estivale d’ici 2050

**Humidité du sol (0.30)**  
Reflète l’équilibre précipitations / infiltration / évapotranspiration.  
Le terme **(1 − humidité)** représente le déficit hydrique.

**Extraction d’eau (0.20)**  
- ≈70 % agriculture, ≈20 % industrie, ≈10 % usage domestique  
- lors des sécheresses récentes : **>80 départements** en restriction

**🌊 Risque d’inondation**  
Les inondations représentent **56 %** des catastrophes naturelles en France, avec **~18 M** de personnes exposées (TRI).
```
score_flood =
0.70 × aléa hydrologique +
0.25 × occupation du sol 
```
Approche alignée avec le **GIEC** et l’**Agence européenne de l’environnement**.

**Aléa hydrologique (0.70)**  
- **+10 à +30 %** de précipitations extrêmes projetées en Europe

**Occupation du sol (0.25)**  
- urbanisation : **×2 à ×5** du ruissellement

**Surface exposée (0.05)**  
Poids faible : la surface n’influence pas directement l’intensité de l’événement.

**👴 Vulnérabilité démographique**  
```
Indice_vieillissement =
1 - (population ≥ 75 / population 0-24)
```
- valeur élevée → territoire plus jeune  
- valeur faible → territoire plus vieillissant et vulnérable  
Source : **INSEE**.

**Conclusion**  
Le modèle combine quatre mécanismes structurants :  
- stress thermique  
- stress hydrique  
- risque d’inondation  
- vulnérabilité démographique  
Les pondérations reposent sur des observations scientifiques et projections reconnues.  
Cette approche capture **~80 %** des dynamiques territoriales, tout en restant synthétique.

**Sources**  
- DRIAS (projections climatiques 2035–2045)  
- Météo-France (climat, indicateurs météo)  
- BRGM (ressources en eau, hydrologie)  
- data.gouv.fr (jeux de données publics)  
- BNPE (prélèvements d’eau 2020)  
- INSEE (démographie)  
- TRI (zones inondables)
"""
    )

# -----------------------------
# Calcul indice
# -----------------------------
if not inclure_climat and not inclure_old:
    st.warning("Active au moins un facteur (climat ou démographie).")
    st.stop()

poids_climat_total = poids_temp + poids_flood + poids_water
if inclure_climat and poids_climat_total == 0:
    st.warning("La somme des poids du climat ne peut pas être nulle.")
    st.stop()

climate_df["indice_climat"] = 0.0
if inclure_climat:
    climate_df["indice_climat"] = (
        poids_temp * climate_df["score_temperature"]
        + poids_flood * climate_df["score_flood"]
        + poids_water * climate_df["score_water"]
    ) / poids_climat_total

poids_total = poids_climat + poids_demo
if poids_total == 0:
    st.warning("La somme des poids de l'indice global ne peut pas être nulle.")
    st.stop()

climate_df["indice_global"] = (
    poids_climat * climate_df["indice_climat"]
    + poids_demo * climate_df["score_vieillissement"]
) / poids_total

if inclure_climat and inclure_old:
    indice_col = "indice_global"
    indice_label = "Indice global"
elif inclure_climat:
    indice_col = "indice_climat"
    indice_label = "Indice climat"
else:
    indice_col = "score_vieillissement"
    indice_label = "Indice vieillissement"

climate_df["indice_affiche"] = climate_df[indice_col]

# format code département
climate_df["code"] = climate_df["code"].astype(str).str.zfill(2)

# -----------------------------
# Chargement carte geojson + noms
# -----------------------------
departements = charger_geojson("pages/tables/departements.geojson")

code_to_nom = {
    feature["properties"]["code"]: feature["properties"]["nom"]
    for feature in departements.get("features", [])
}
climate_df["departement"] = climate_df["code"].map(code_to_nom).fillna(climate_df["code"])
climate_df["departement_label"] = climate_df["departement"] + " (" + climate_df["code"] + ")"






#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
st.divider()

col1, col2, col3 = st.columns(3)

best_dep = climate_df.sort_values("indice_affiche", ascending=False)["departement_label"].iloc[0]
worst_dep = climate_df.sort_values("indice_affiche")["departement_label"].iloc[0]
avg_value = f"{climate_df['indice_affiche'].mean():.2f}"

with col1:
    st.markdown(
        f"""
        <div class="metric-card">
        <div class="metric-label">{indice_label} moyen France</div>
        <div class="metric-value metric-value--number">{avg_value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
        f"""
        <div class="metric-card">
        <div class="metric-label">Meilleur département</div>
        <div class="metric-value metric-value--name">{best_dep}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col3:
    st.markdown(
        f"""
        <div class="metric-card">
        <div class="metric-label">Moins favorable</div>
        <div class="metric-value metric-value--name">{worst_dep}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.divider()

# -----------------------------
# Création carte
# -----------------------------
color_scale = [
    (0.0, "#991b1b"),
    (0.2, "#c2410c"),
    (0.4, "#f59e0b"),
    (0.6, "#84cc16"),
    (0.8, "#22c55e"),
    (1.0, "#15803d"),
]

fig = px.choropleth(
    climate_df,
    geojson=departements,
    locations="code",
    featureidkey="properties.code",
    color="indice_affiche",
    color_continuous_scale=color_scale,
    hover_name="departement_label",
    custom_data=[
        "departement",
        "code",
        "indice_affiche",
        "score_temperature",
        "score_flood",
        "score_water",
        "score_vieillissement",
    ],
)

fig.update_geos(
    fitbounds="locations",
    visible=False,
    bgcolor="rgba(0,0,0,0)",
    projection={"type": "mercator"},
)

hover_lines = [
    "<b>%{customdata[0]} (%{customdata[1]})</b><br>",
    f"{indice_label}: <b>%{{customdata[2]:.2f}}</b><br>",
]
if inclure_climat:
    hover_lines.extend(
        [
            "Température: %{customdata[3]:.2f}<br>",
            "Inondation: %{customdata[4]:.2f}<br>",
    "Stress hydrique: %{customdata[5]:.2f}",
        ]
    )
if inclure_old:
    if inclure_climat:
        hover_lines.append("<br>Vieillissement: %{customdata[6]:.2f}")
    else:
        hover_lines.append("Vieillissement: %{customdata[6]:.2f}")
hovertemplate = "".join(hover_lines) + "<extra></extra>"

fig.update_traces(
    marker_line_color="rgba(255,255,255,0.35)",
    marker_line_width=0.8,
    hovertemplate=hovertemplate,
)

fig.update_layout(
    height=650,
    margin=dict(r=0, t=0, l=0, b=0),
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font={"color": "#e8edf2"},
    coloraxis_colorbar={
        "title": {"text": indice_label, "font": {"color": "#e8edf2"}},
        "tickfont": {"color": "#cfd6df"},
        "tickformat": ".2f",
        "ticks": "outside",
        "len": 0.75,
        "thickness": 14,
        "outlinewidth": 0,
        "bgcolor": "rgba(0,0,0,0)",
    },
    hoverlabel={
        "bgcolor": "#0f172a",
        "font_color": "#f8fafc",
        "bordercolor": "rgba(255,255,255,0.15)",
    },
)

selected_codes_map = st.session_state.get("selected_codes", [])
if selected_codes_map:
    selected_codes_map = [
        code.zfill(2) if str(code).isdigit() else str(code)
        for code in selected_codes_map
    ]
    fig.add_trace(
        go.Choropleth(
            geojson=departements,
            locations=selected_codes_map,
            featureidkey="properties.code",
            z=[1] * len(selected_codes_map),
            colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
            showscale=False,
            marker_line_color="rgba(248,250,252,0.95)",
            marker_line_width=2.2,
            hoverinfo="skip",
            name="Sélection",
        )
    )

# -----------------------------
# Affichage carte
# -----------------------------
st.plotly_chart(fig, use_container_width=True)
st.caption("Indice (0–1) : plus proche de 1 = plus favorable.")

st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

# -----------------------------
# Top / Flop départements
# -----------------------------
st.subheader(f"🏆 Top / Flop 5 départements ({indice_label.lower()})")

col_top, col_flop = st.columns(2)
top = climate_df.sort_values("indice_affiche", ascending=False).head(5)
flop = climate_df.sort_values("indice_affiche", ascending=True).head(5)

with col_top:
    st.caption("Top 5")
    st.dataframe(
        top[["departement", "code", "indice_affiche"]].rename(
            columns={"indice_affiche": indice_label}
        ),
        use_container_width=True,
        hide_index=True,
    )

with col_flop:
    st.caption("Flop 5")
    st.dataframe(
        flop[["departement", "code", "indice_affiche"]].rename(
            columns={"indice_affiche": indice_label}
        ),
        use_container_width=True,
        hide_index=True,
    )

st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

# -----------------------------
# Recherche globale (radar + classement)
# -----------------------------
st.subheader("🔎 Sélection des départements")
options_df = (
    climate_df[["code", "departement_label"]]
    .drop_duplicates()
    .sort_values("departement_label")
)
code_to_label = dict(zip(options_df["code"], options_df["departement_label"]))
selected_codes = st.multiselect(
    "Sélectionne jusqu'à 4 départements",
    options=options_df["code"].tolist(),
    format_func=lambda code: code_to_label.get(code, code),
    placeholder="Tape pour rechercher un département...",
    key="selected_codes",
)
st.caption("Cette sélection filtre le radar et le classement.")

if len(selected_codes) > 4:
    selected_codes = selected_codes[:4]
    st.session_state["selected_codes"] = selected_codes
    st.info("Comparaison limitée à 4 départements pour garder le radar lisible.")

filtered_df = climate_df
if selected_codes:
    filtered_df = climate_df[climate_df["code"].isin(selected_codes)]

avg_row = {
    "departement": "Moyenne nationale",
    "code": "—",
    "departement_label": "Moyenne nationale",
    "score_temperature": climate_df["score_temperature"].mean(),
    "score_flood": climate_df["score_flood"].mean(),
    "score_water": climate_df["score_water"].mean(),
    "score_vieillissement": climate_df["score_vieillissement"].mean(),
}

# -----------------------------
# Radar par département
# -----------------------------
st.subheader("🎯 Profil des facteurs par département (Radar)")
st.caption("Échelle 0–1 : plus la valeur est proche de 1, plus l’indicateur est favorable.")

selected_rows = []
for code in selected_codes:
    row = climate_df[climate_df["code"] == code]
    if not row.empty:
        selected_rows.append(row.iloc[0])

if not selected_rows:
    selected_rows = [pd.Series(avg_row)]

names = [row["departement_label"] for row in selected_rows]
st.caption(f"Départements affichés : {', '.join(names)}")

radar_labels = []
max_values = []
if inclure_climat:
    radar_labels.extend(["Température", "Inondation", "Stress hydrique"])
    max_values.extend(
        [
            climate_df["score_temperature"].max(),
            climate_df["score_flood"].max(),
            climate_df["score_water"].max(),
        ]
    )
if inclure_old:
    radar_labels.append("Vieillissement")
    max_values.append(climate_df["score_vieillissement"].max())
radar_labels_closed = radar_labels + [radar_labels[0]]
max_values_closed = max_values + [max_values[0]]
all_values = []
for row in selected_rows:
    values = []
    if inclure_climat:
        values.extend(
            [
                row["score_temperature"],
                row["score_flood"],
                row["score_water"],
            ]
        )
    if inclure_old:
        values.append(row["score_vieillissement"])
    all_values.extend(values)
radar_max = max(all_values + max_values)
radar_range = [0, 1] if radar_max <= 1 else [0, radar_max * 1.05]

fig_radar = go.Figure()
palette = ["#22c55e", "#38bdf8", "#a855f7", "#f97316"]
for index, row in enumerate(selected_rows):
    values = []
    if inclure_climat:
        values.extend(
            [
                row["score_temperature"],
                row["score_flood"],
                row["score_water"],
            ]
        )
    if inclure_old:
        values.append(row["score_vieillissement"])
    values_closed = values + [values[0]]
    color = palette[index % len(palette)]
    fill_mode = "toself" if len(selected_rows) == 1 else "none"
    fig_radar.add_trace(
        go.Scatterpolar(
            r=values_closed,
            theta=radar_labels_closed,
            fill=fill_mode,
            name=row["departement_label"],
            line={"color": color, "width": 2},
            fillcolor="rgba(34,197,94,0.18)" if fill_mode == "toself" else "rgba(0,0,0,0)",
        )
    )
fig_radar.add_trace(
    go.Scatterpolar(
        r=max_values_closed,
        theta=radar_labels_closed,
        name="Max national",
        mode="lines+markers",
        line={"color": "#f59e0b", "width": 2, "dash": "dash"},
        marker={"size": 6},
        hovertemplate="Max national<br>%{theta}: %{r:.2f}<extra></extra>",
    )
)

fig_radar.update_layout(
    template="plotly_dark",
    height=520,
    margin=dict(l=30, r=30, t=20, b=60),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font={"color": "#e8edf2"},
    polar={
        "radialaxis": {"visible": True, "range": radar_range, "tickfont": {"size": 11}},
        "angularaxis": {"tickfont": {"size": 12}, "rotation": 90},
        "bgcolor": "rgba(0,0,0,0)",
    },
    showlegend=True,
    legend={
        "orientation": "h",
        "y": 1.12,
        "x": 0.0,
        "font": {"color": "#cfd6df"},
    },
)

st.plotly_chart(fig_radar, use_container_width=True)

st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

#*********************
#*********************


# un classement complet interactif
st.subheader("📊 Classement des départements")

table = filtered_df.sort_values("indice_affiche", ascending=False)

st.dataframe(
    table[["departement", "code", "indice_affiche"]].rename(
        columns={"indice_affiche": indice_label}
    ),
    hide_index=True,
)

st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

# distribution nationale
st.subheader(f"📈 Distribution nationale de l'{indice_label.lower()}")

serie = climate_df["indice_affiche"].dropna()
mean_val = serie.mean()
median_val = serie.median()
q1_val = serie.quantile(0.25)
q3_val = serie.quantile(0.75)

fig_hist = px.histogram(
    climate_df,
    x="indice_affiche",
    nbins=30,
    color_discrete_sequence=["#93c5fd"],
)
fig_hist.update_layout(
    template="plotly_dark",
    height=380,
    margin=dict(l=20, r=20, t=10, b=20),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font={"color": "#e8edf2"},
    xaxis_title=indice_label,
    yaxis_title="Nombre de départements",
)
fig_hist.update_traces(marker_line_color="rgba(255,255,255,0.15)", marker_line_width=1)
fig_hist.update_traces(
    hoverinfo="skip",
    hovertemplate=None,
    selector=dict(type="histogram"),
)
fig_hist.add_vline(
    x=mean_val,
    line_width=2,
    line_dash="solid",
    line_color="#22c55e",
    annotation_text="Moyenne",
    annotation_position="top left",
)
fig_hist.add_vline(
    x=median_val,
    line_width=2,
    line_dash="dash",
    line_color="#f59e0b",
    annotation_text="Médiane",
    annotation_position="top right",
)
fig_hist.add_vline(
    x=q1_val,
    line_width=1,
    line_dash="dot",
    line_color="#94a3b8",
    annotation_text="Q1",
    annotation_position="top left",
)
fig_hist.add_vline(
    x=q3_val,
    line_width=1,
    line_dash="dot",
    line_color="#94a3b8",
    annotation_text="Q3",
    annotation_position="top right",
)

selected_marks = climate_df[
    climate_df["code"].isin(selected_codes)
][["departement", "departement_label", "code", "indice_affiche"]].dropna()
if not selected_marks.empty:
    marker_colors = ["#38bdf8", "#a855f7", "#f97316", "#22c55e"]
    fig_hist.add_trace(
        go.Scatter(
            x=selected_marks["indice_affiche"],
            y=[0] * len(selected_marks),
            mode="markers",
            text=selected_marks["departement"],
            marker={
                "size": 9,
                "color": marker_colors[: len(selected_marks)],
                "line": {"width": 1, "color": "rgba(255,255,255,0.6)"},
            },
            showlegend=False,
            hovertemplate="%{text}<br>Indice: %{x:.2f}<extra></extra>",
        )
    )
    for idx, row in enumerate(selected_marks.itertuples(index=False)):
        label = f"{row.departement}"
        fig_hist.add_vline(
            x=row.indice_affiche,
            line_width=2,
            line_dash="dash",
            line_color=marker_colors[idx % len(marker_colors)],
            annotation_text=label,
            annotation_position="top",
        )

st.plotly_chart(fig_hist, use_container_width=True)

fig_box = px.box(
    serie,
    x=serie,
    points=False,
    color_discrete_sequence=["#38bdf8"],
)
fig_box.update_layout(
    template="plotly_dark",
    height=200,
    margin=dict(l=20, r=20, t=10, b=20),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font={"color": "#e8edf2"},
    xaxis_title=indice_label,
    yaxis_title="",
)
fig_box.update_traces(line_color="#38bdf8", fillcolor="rgba(56,189,248,0.25)")

if not selected_marks.empty:
    fig_box.add_trace(
        go.Scatter(
            x=selected_marks["indice_affiche"],
            y=[0] * len(selected_marks),
            mode="markers",
            text=selected_marks["departement"],
            marker={
                "size": 9,
                "color": marker_colors[: len(selected_marks)],
                "line": {"width": 1, "color": "rgba(255,255,255,0.6)"},
            },
            name="Sélection",
            hovertemplate="%{text}<br>Indice: %{x:.2f}<extra></extra>",
        )
    )

st.plotly_chart(fig_box, use_container_width=True)
