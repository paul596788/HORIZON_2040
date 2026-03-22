import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.department_scores import calculer_scores_departements
from utils.excel_helpers import charger_geojson, render_global_department_selector

MAJOR_CITIES = [
    {"name": "Paris", "lat": 48.8566, "lon": 2.3522, "textposition": "top center"},
    {"name": "Lille", "lat": 50.6292, "lon": 3.0573, "textposition": "top left"},
    {"name": "Rouen", "lat": 49.4431, "lon": 1.0993, "textposition": "bottom left"},
    {"name": "Reims", "lat": 49.2583, "lon": 4.0317, "textposition": "top right"},
    {"name": "Strasbourg", "lat": 48.5734, "lon": 7.7521, "textposition": "middle right"},
    {"name": "Dijon", "lat": 47.3220, "lon": 5.0415, "textposition": "bottom right"},
    {"name": "Rennes", "lat": 48.1173, "lon": -1.6778, "textposition": "bottom left"},
    {"name": "Brest", "lat": 48.3904, "lon": -4.4861, "textposition": "top left"},
    {"name": "Nantes", "lat": 47.2184, "lon": -1.5536, "textposition": "top left"},
    {"name": "Tours", "lat": 47.3941, "lon": 0.6848, "textposition": "bottom left"},
    {"name": "Bordeaux", "lat": 44.8378, "lon": -0.5792, "textposition": "top left"},
    {"name": "Toulouse", "lat": 43.6047, "lon": 1.4442, "textposition": "bottom left"},
    {"name": "Montpellier", "lat": 43.6119, "lon": 3.8772, "textposition": "top left"},
    {"name": "Clermont-Ferrand", "lat": 45.7772, "lon": 3.0870, "textposition": "middle left"},
    {"name": "Lyon", "lat": 45.7640, "lon": 4.8357, "textposition": "top right"},
    {"name": "Grenoble", "lat": 45.1885, "lon": 5.7245, "textposition": "bottom right"},
    {"name": "Marseille", "lat": 43.2965, "lon": 5.3698, "textposition": "bottom right"},
    {"name": "Nice", "lat": 43.7102, "lon": 7.2620, "textposition": "middle right"},
]


st.set_page_config(page_title="HORIZON 2040", layout="wide")

st.markdown(
    """
<style>
.stApp {
background: radial-gradient(1200px 800px at 20% 0%, #111827 0%, #0b0f15 45%, #090c12 100%);
color: #e5e7eb;
}
.block-container {
padding-top: 2.2rem;
padding-bottom: 3rem;
max-width: 1280px;
}
.hero-header {
display: flex;
justify-content: center;
align-items: center;
gap: 1rem;
flex-wrap: wrap;
width: 100%;
padding: 0.15rem 0 1rem 0;
margin: 0 0 0.4rem 0;
overflow: visible;
}
.hero-logo {
font-size: clamp(3.2rem, 5.4vw, 4.8rem);
line-height: 1;
display: inline-flex;
align-items: center;
justify-content: center;
}
.hero-text {
font-size: clamp(3rem, 7vw, 5.4rem);
font-weight: 800;
letter-spacing: -0.05em;
line-height: 1.02;
color: #f8fafc;
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
.concept-card {
background: linear-gradient(180deg, rgba(15,23,42,0.82) 0%, rgba(17,24,39,0.9) 100%);
border: 1px solid rgba(148,163,184,0.18);
border-radius: 18px;
padding: 22px 24px;
margin: 0.3rem auto 0.4rem auto;
max-width: 1120px;
}
.concept-kicker {
color: #93c5fd;
font-size: 0.78rem;
font-weight: 700;
letter-spacing: 0.08em;
text-transform: uppercase;
margin-bottom: 0.45rem;
}
.concept-title {
color: #f8fafc;
font-size: 1.35rem;
font-weight: 700;
line-height: 1.35;
margin-bottom: 0.9rem;
max-width: 980px;
}
.concept-body {
color: #dbe4ee;
font-size: 1.02rem;
line-height: 1.6;
max-width: 980px;
}
.trust-grid {
display: grid;
grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
gap: 14px;
margin-top: 1.1rem;
}
.trust-card {
background: rgba(255,255,255,0.03);
border: 1px solid rgba(148,163,184,0.12);
border-radius: 16px;
padding: 14px 15px;
}
.trust-title {
color: #f8fafc;
font-size: 0.96rem;
font-weight: 700;
margin-bottom: 0.35rem;
}
.trust-body {
color: #cbd5e1;
font-size: 0.92rem;
line-height: 1.5;
}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="hero-header">
  <div class="hero-logo">🌍</div>
  <div class="hero-text">HORIZON 2040</div>
</div>
""",
    unsafe_allow_html=True,
)

with st.expander("🌐 Le concept", expanded=False):
    st.markdown(
        """
<div class="concept-card">
  <div class="concept-kicker">Le concept</div>
  <div class="concept-title">Un outil d’aide à la décision territoriale construit à partir de données publiques, traçables et comparables.</div>
  <div class="concept-body">
    HORIZON 2040 agrège des indicateurs climatiques, démographiques, économiques, sanitaires,
    immobiliers, éducatifs, numériques et territoriaux afin de produire une lecture synthétique
    des départements français. L’utilisateur ajuste le poids de chaque critère selon son scénario
    d’usage : implantation, investissement, attractivité ou qualité de vie.
  </div>
  <div class="trust-grid">
    <div class="trust-card">
      <div class="trust-title">Sources publiques officielles</div>
      <div class="trust-body">Les indicateurs reposent sur des bases ouvertes issues d’organismes publics français et de référentiels reconnus.</div>
    </div>
    <div class="trust-card">
      <div class="trust-title">Méthode multicritère</div>
      <div class="trust-body">Chaque score est normalisé puis combiné dans un indice composite configurable pour tester différents scénarios.</div>
    </div>
    <div class="trust-card">
      <div class="trust-title">Lecture fiable et transparente</div>
      <div class="trust-body">L’outil est conçu comme une aide à la décision, avec traçabilité des sources et explicitation des hypothèses de lecture.</div>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

with st.expander("Méthodologie, fiabilité et sources", expanded=False):
    st.markdown(
        """
### Cadre d’utilisation

- **Finalité** : HORIZON 2040 est un outil d’aide à la décision territoriale destiné à l’exploration, à la comparaison et à la priorisation de départements.
- **Méthode** : les indicateurs sont harmonisés, normalisés puis agrégés dans un score composite pondérable par l’utilisateur.
- **Public visé** : particuliers, investisseurs, décideurs publics, analystes territoriaux et acteurs de l’attractivité.
- **Prudence de lecture** : l’outil ne remplace ni une étude réglementaire, ni un audit local, ni une expertise métier. Il permet une lecture structurée et comparable des territoires.

### Principes de fiabilité

- **Traçabilité** : recours à des sources publiques, institutionnelles ou de référence.
- **Comparabilité** : lecture homogène des indicateurs à l’échelle départementale.
- **Transparence** : pondérations ajustables selon le scénario d’usage.
- **Robustesse** : croisement de dimensions complémentaires, sans se limiter à un seul indicateur.

### Sources statistiques générales

- **INSEE**. Institut national de la statistique et des études économiques. Données sur la démographie, l’économie, l’emploi, les revenus et le logement. [https://www.insee.fr](https://www.insee.fr)
- **data.gouv.fr**. Plateforme ouverte des données publiques françaises. Agrégation de bases issues de ministères, collectivités et organismes publics. [https://www.data.gouv.fr](https://www.data.gouv.fr)
- **OpenDataFrance**. Données territoriales et locales produites par les collectivités. [https://www.opendatafrance.net](https://www.opendatafrance.net)

### Climat et environnement

- **Météo-France**. Données météorologiques historiques et en temps réel. [https://donneespubliques.meteofrance.fr](https://donneespubliques.meteofrance.fr)
- **ADEME**. Données sur l’énergie, les émissions, les déchets et la transition écologique. [https://data.ademe.fr](https://data.ademe.fr)
- **Géorisques**. Bases de données sur les risques naturels et technologiques. [https://www.georisques.gouv.fr](https://www.georisques.gouv.fr)

### Immobilier et logement

- **Demandes de Valeurs Foncières (DVF)**. Transactions immobilières. [https://www.data.gouv.fr/fr/datasets/demandes-de-valeurs-foncieres](https://www.data.gouv.fr/fr/datasets/demandes-de-valeurs-foncieres)
- **INSEE**. Statistiques sur le parc immobilier, les loyers et la construction. [https://www.insee.fr](https://www.insee.fr)
- **DataFrance**. Indicateurs territoriaux incluant immobilier et attractivité. [https://datafrance.info](https://datafrance.info)

### Emploi et économie

- **Pôle emploi**. Données sur le marché du travail.
- **URSSAF**. Données sur les salaires et l’activité économique.
- **Banque de France**. Données macroéconomiques, entreprises et crédit.

### Santé publique

- **Santé publique France**. Indicateurs sanitaires, épidémiologie et prévention.
- **Assurance Maladie**. Données sur les dépenses de santé et les soins.

### Criminalité et sécurité

- **Ministère de l’Intérieur**. Statistiques sur la délinquance, la criminalité et la sécurité publique.
- **ONDRP**. Données historiques sur la délinquance.

### Numérique et infrastructures

- **ARCEP**. Données sur la couverture fibre, internet et réseaux mobiles.
- **ANFR**. Données sur les antennes et infrastructures radio.

### Ressources en eau

- **BNPE**. Banque Nationale des Prélèvements en Eau. Données sur les prélèvements d’eau par secteur.

### Données géographiques

- **IGN**. Données cartographiques, topographiques et géolocalisées.
- **Base Adresse Nationale**. Référentiel officiel des adresses géolocalisées.

### Sources internationales complémentaires

- **Eurostat**. Données statistiques comparatives à l’échelle européenne.
- **OCDE**. Indicateurs économiques et sociaux internationaux.
- **CEPII**. Analyses et bases de données sur le commerce international.
"""
    )

scores = calculer_scores_departements(cache_version="exclude-outremer-v1")
geojson_departements = charger_geojson("assets/departements.geojson")

theme_groups = {
    "🌍 Contraintes 2040": {
        "Climat": "Score climat",
        "Transition démographique": "Score transition démographique",
    },
    "🧭 Conditions de vie": {
        "Emploi": "Score emploi",
        "Étudiants": "Score étudiants",
        "Revenu": "Score revenu",
        "Santé": "Score santé",
        "Éducation": "Score éducation",
        "Fibre": "Score internet",
        "Sécurité": "Score criminalité",
        "Immobilier": "Score immobilier",
    },
}
themes = {theme: column for group in theme_groups.values() for theme, column in group.items()}
theme_order = [theme for group in theme_groups.values() for theme in group.keys()]

st.sidebar.header("🎯 Mes critères")
selection_themes = st.sidebar.multiselect(
    "Critères à prendre en compte",
    theme_order,
    default=theme_order,
)

if not selection_themes:
    st.warning("Sélectionne au moins un critère pour calculer le score global.")
    st.stop()

st.sidebar.caption("Le score global personnalisé est une moyenne pondérée des critères actifs.")
poids = {}
for group_index, (group_name, group_themes) in enumerate(theme_groups.items()):
    themes_in_group = [theme for theme in group_themes.keys() if theme in selection_themes]
    if not themes_in_group:
        continue

    if group_index > 0:
        st.sidebar.divider()

    st.sidebar.subheader(group_name)
    for theme in themes_in_group:
        poids[theme] = st.sidebar.slider(
            f"Poids {theme}",
            min_value=0.0,
            max_value=1.0,
            value=1.0,
            step=0.05,
            key=f"poids_{theme}",
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

st.subheader("Synthèse")
col1, col2, col3 = st.columns(3)
col1.metric("Score moyen national", f"{scores['Score global personnalisé'].mean():.2f}")
col2.metric("Meilleur département", scores.iloc[0]["Département"])
col3.metric("Score du leader", f"{scores.iloc[0]['Score global personnalisé']:.2f}")

st.subheader("Sélection des départements")
departements_selectionnes = render_global_department_selector(
    title=None,
    caption="La sélection est partagée entre les pages et pilote les comparaisons du tableau de bord.",
)
departements_selectionnes = [
    departement for departement in departements_selectionnes if departement in set(scores["Département"])
]

map_controls_col, map_info_col = st.columns([1.1, 3])
with map_controls_col:
    afficher_villes = st.checkbox(
        "Afficher les grandes villes",
        value=False,
        help="Affiche des repères urbains sur la carte principale.",
    )
with map_info_col:
    st.caption(
        "Option cartographique : active les principales métropoles françaises pour ajouter "
        "des repères visuels sans surcharger la carte par défaut."
    )

color_scale = [
    (0.0, "#991b1b"),
    (0.2, "#c2410c"),
    (0.4, "#f59e0b"),
    (0.6, "#84cc16"),
    (0.8, "#22c55e"),
    (1.0, "#15803d"),
]

scores_carte = scores.copy()
carte_colonne = "Score global personnalisé"
carte_titre = "Score"
range_color = (0, 1)

if len(selection_themes) == 1:
    theme_unique = selection_themes[0]
    carte_colonne = themes[theme_unique]
    carte_titre = theme_unique
    serie_carte = scores_carte[carte_colonne].dropna()
    if not serie_carte.empty:
        q05 = float(serie_carte.quantile(0.05))
        q95 = float(serie_carte.quantile(0.95))
        if q95 > q05:
            range_color = (q05, q95)
        else:
            range_color = (float(serie_carte.min()), float(serie_carte.max()))

fig = px.choropleth(
    scores_carte,
    geojson=geojson_departements,
    locations="Département",
    featureidkey="properties.nom",
    color=carte_colonne,
    color_continuous_scale=color_scale,
    range_color=range_color,
    hover_name="Département",
    custom_data=["Département", "Région", "Score global personnalisé"] + colonnes_selectionnees,
)

hover_lines = [
    "<b>%{customdata[0]}</b><br>",
    "Région: %{customdata[1]}<br>",
    "Score global: <b>%{customdata[2]:.2f}</b><br>",
]
for idx, theme in enumerate(selection_themes, start=3):
    hover_lines.append(f"{theme}: %{{customdata[{idx}]:.2f}}<br>")
hovertemplate = "".join(hover_lines) + "<extra></extra>"

fig.update_geos(
    fitbounds="locations",
    visible=False,
    projection={"type": "mercator"},
    bgcolor="rgba(0,0,0,0)",
)
fig.update_traces(
    marker_line_color="rgba(255,255,255,0.25)",
    marker_line_width=0.8,
    hovertemplate=hovertemplate,
)
if departements_selectionnes:
    fig.add_trace(
        go.Choropleth(
            geojson=geojson_departements,
            locations=departements_selectionnes,
            featureidkey="properties.nom",
            z=[1] * len(departements_selectionnes),
            colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
            showscale=False,
            marker_line_color="rgba(248,250,252,0.95)",
            marker_line_width=2.4,
            hoverinfo="skip",
            name="Sélection",
        )
    )
if afficher_villes:
    fig.add_trace(
        go.Scattergeo(
            lon=[city["lon"] for city in MAJOR_CITIES],
            lat=[city["lat"] for city in MAJOR_CITIES],
            mode="markers",
            marker={
                "size": 15,
                "color": "rgba(56, 189, 248, 0.18)",
                "line": {"width": 0},
            },
            hoverinfo="skip",
            showlegend=False,
        )
    )
    fig.add_trace(
        go.Scattergeo(
            lon=[city["lon"] for city in MAJOR_CITIES],
            lat=[city["lat"] for city in MAJOR_CITIES],
            text=[city["name"] for city in MAJOR_CITIES],
            mode="markers+text",
            textposition=[city["textposition"] for city in MAJOR_CITIES],
            textfont={"size": 11, "color": "#f8fafc"},
            marker={
                "size": 6.8,
                "color": "#38bdf8",
                "line": {"color": "#f8fafc", "width": 1.2},
            },
            hovertemplate="<b>%{text}</b><br>Grande ville repère<extra></extra>",
            showlegend=False,
        )
    )
fig.update_layout(
    template="plotly_dark",
    height=680,
    margin={"l": 0, "r": 0, "t": 0, "b": 0},
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font={"color": "#e8edf2"},
    coloraxis_colorbar={
        "title": {"text": carte_titre, "font": {"color": "#e8edf2"}},
        "tickfont": {"color": "#cfd6df"},
        "bgcolor": "rgba(0,0,0,0)",
        "len": 0.78,
        "thickness": 14,
        "outlinewidth": 0,
    },
    hoverlabel={
        "bgcolor": "#0f172a",
        "font_color": "#f8fafc",
        "bordercolor": "rgba(255,255,255,0.15)",
    },
)
st.plotly_chart(fig, use_container_width=True)
st.caption(
    "Score 0–1 : plus proche de 1 = plus favorable selon les pondérations choisies. "
    + ("Les grandes villes françaises sont affichées comme repères." if afficher_villes else "Les grandes villes peuvent être affichées à la demande.")
)

st.divider()
st.subheader("Top / Flop 5")
col_top, col_flop = st.columns(2)
top = scores.head(5)
flop = scores.tail(5).sort_values("Score global personnalisé", ascending=True)

with col_top:
    st.caption("Top 5")
    st.dataframe(
        top[["Département", "Région", "Score global personnalisé"]],
        use_container_width=True,
        hide_index=True,
    )

with col_flop:
    st.caption("Flop 5")
    st.dataframe(
        flop[["Département", "Région", "Score global personnalisé"]],
        use_container_width=True,
        hide_index=True,
    )

filtered_df = scores[scores["Département"].isin(departements_selectionnes)] if departements_selectionnes else scores

st.subheader("Profil des critères par département")
st.caption("Échelle 0–1 : plus la valeur est proche de 1, plus le critère est favorable.")

selected_rows = []
for departement in departements_selectionnes:
    row = scores[scores["Département"] == departement]
    if not row.empty:
        selected_rows.append(row.iloc[0])

has_selected_rows = bool(selected_rows)
if not selected_rows:
    moyenne = {"Département": "Moyenne nationale"}
    for colonne in colonnes_selectionnees:
        moyenne[colonne] = scores[colonne].mean()
    selected_rows = [moyenne]

radar_preferred_order = [
    "Emploi",
    "Étudiants",
    "Revenu",
    "Santé",
    "Climat",
    "Fibre",
    "Sécurité",
    "Éducation",
    "Transition démographique",
    "Immobilier",
]
radar_labels = [theme for theme in radar_preferred_order if theme in selection_themes]
radar_labels += [theme for theme in selection_themes if theme not in radar_labels]
radar_labels_closed = radar_labels + [radar_labels[0]]
fig_radar = go.Figure()
palette = ["#22c55e", "#38bdf8", "#a855f7", "#f97316"]

if has_selected_rows:
    mean_values = [scores[themes[theme]].mean() for theme in radar_labels]
    fig_radar.add_trace(
        go.Scatterpolar(
            r=mean_values + [mean_values[0]],
            theta=radar_labels_closed,
            name="Moyenne nationale",
            mode="lines",
            line={"color": "rgba(148,163,184,0.65)", "width": 1.4, "dash": "dot"},
            hovertemplate="Moyenne nationale<br>%{theta}: %{r:.2f}<extra></extra>",
        )
    )

for index, row in enumerate(selected_rows):
    values = [row[themes[theme]] for theme in radar_labels]
    values_closed = values + [values[0]]
    name = row["Département"] if isinstance(row, dict) else row["Département"]
    fig_radar.add_trace(
        go.Scatterpolar(
            r=values_closed,
            theta=radar_labels_closed,
            fill="toself" if len(selected_rows) == 1 else "none",
            name=name,
            line={"color": palette[index % len(palette)], "width": 2},
            fillcolor="rgba(34,197,94,0.16)" if len(selected_rows) == 1 else "rgba(0,0,0,0)",
        )
    )

max_values = [scores[themes[theme]].max() for theme in radar_labels]
fig_radar.add_trace(
    go.Scatterpolar(
        r=max_values + [max_values[0]],
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
        "radialaxis": {"visible": True, "range": [0, 1], "tickfont": {"size": 11}},
        "angularaxis": {"tickfont": {"size": 12}, "rotation": 90},
        "bgcolor": "rgba(0,0,0,0)",
    },
    showlegend=True,
    legend={"orientation": "h", "y": 1.12, "x": 0.0},
)
st.plotly_chart(fig_radar, use_container_width=True)

st.divider()
st.subheader("Distribution nationale")
serie = scores["Score global personnalisé"].dropna()
mean_val = serie.mean()
median_val = serie.median()
q1_val = serie.quantile(0.25)
q3_val = serie.quantile(0.75)

fig_hist = px.histogram(
    scores,
    x="Score global personnalisé",
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
    xaxis_title="Score global personnalisé",
    yaxis_title="Nombre de départements",
)
fig_hist.update_traces(marker_line_color="rgba(255,255,255,0.15)", marker_line_width=1)
fig_hist.add_vline(x=mean_val, line_width=2, line_dash="solid", line_color="#22c55e", annotation_text="Moyenne")
fig_hist.add_vline(x=median_val, line_width=2, line_dash="dash", line_color="#f59e0b", annotation_text="Médiane")
fig_hist.add_vline(x=q1_val, line_width=1, line_dash="dot", line_color="#94a3b8", annotation_text="Q1")
fig_hist.add_vline(x=q3_val, line_width=1, line_dash="dot", line_color="#94a3b8", annotation_text="Q3")

selected_marks = scores[scores["Département"].isin(departements_selectionnes)][
    ["Département", "Score global personnalisé"]
].dropna()
if not selected_marks.empty:
    marker_colors = ["#38bdf8", "#a855f7", "#f97316", "#22c55e"]
    fig_hist.add_trace(
        go.Scatter(
            x=selected_marks["Score global personnalisé"],
            y=[0] * len(selected_marks),
            mode="markers",
            text=selected_marks["Département"],
            marker={
                "size": 9,
                "color": marker_colors[: len(selected_marks)],
                "line": {"width": 1, "color": "rgba(255,255,255,0.6)"},
            },
            showlegend=False,
            hovertemplate="%{text}<br>Score: %{x:.2f}<extra></extra>",
        )
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
    xaxis_title="Score global personnalisé",
    yaxis_title="",
)
fig_box.update_traces(line_color="#38bdf8", fillcolor="rgba(56,189,248,0.25)")
if not selected_marks.empty:
    marker_colors = ["#38bdf8", "#a855f7", "#f97316", "#22c55e"]
    fig_box.add_trace(
        go.Scatter(
            x=selected_marks["Score global personnalisé"],
            y=[0] * len(selected_marks),
            mode="markers",
            text=selected_marks["Département"],
            marker={
                "size": 9,
                "color": marker_colors[: len(selected_marks)],
                "line": {"width": 1, "color": "rgba(255,255,255,0.6)"},
            },
            name="Sélection",
            hovertemplate="%{text}<br>Score: %{x:.2f}<extra></extra>",
        )
    )
st.plotly_chart(fig_box, use_container_width=True)

st.caption(
    "Lecture des notes: 0 = moins favorable dans l'échantillon, 1 = plus favorable. "
    "Le score global personnalisé est une moyenne pondérée des critères sélectionnés."
)

st.divider()
st.subheader("Classement des départements")
st.dataframe(
    filtered_df[
        ["Département", "Région"] + colonnes_selectionnees + ["Score global personnalisé"]
    ].style.format({col: "{:.2f}" for col in colonnes_selectionnees + ["Score global personnalisé"]}),
    use_container_width=True,
    hide_index=True,
)
