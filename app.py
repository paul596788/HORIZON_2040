import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.department_scores import calculer_scores_departements
from utils.excel_helpers import charger_geojson


st.set_page_config(page_title="Dashboard socio-economique", layout="wide")

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
</style>
""",
    unsafe_allow_html=True,
)

st.title("Où vivre en France en 2040 ?")
st.caption(
    "Indice composite exploratoire pour comparer les départements selon tes priorités "
    "socio-économiques et territoriales."
)

scores = calculer_scores_departements()
geojson_departements = charger_geojson("assets/departements.geojson")

themes = {
    "Emploi": "Score emploi",
    "Étudiants": "Score étudiants",
    "Revenu": "Score revenu",
    "Santé": "Score santé",
    "Climat": "Score climat",
    "Internet": "Score internet",
    "Criminalité": "Score criminalité",
    "Éducation": "Score éducation",
    "Immobilier": "Score immobilier",
}

st.sidebar.header("⚙️ Pondération des critères")
selection_themes = st.sidebar.multiselect(
    "Critères à prendre en compte",
    list(themes.keys()),
    default=list(themes.keys()),
)

if not selection_themes:
    st.warning("Sélectionne au moins un critère pour calculer le score global.")
    st.stop()

st.sidebar.caption("Le score global personnalisé est une moyenne pondérée des critères actifs.")
poids = {}
for theme in selection_themes:
    poids[theme] = st.sidebar.slider(
        f"Poids {theme}",
        min_value=0.0,
        max_value=1.0,
        value=1.0,
        step=0.1,
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
col1.metric("Départements comparés", f"{scores['Département'].nunique()}")
col2.metric("Meilleur département", scores.iloc[0]["Département"])
col3.metric("Score du leader", f"{scores.iloc[0]['Score global personnalisé']:.2f}")

color_scale = [
    (0.0, "#991b1b"),
    (0.2, "#c2410c"),
    (0.4, "#f59e0b"),
    (0.6, "#84cc16"),
    (0.8, "#22c55e"),
    (1.0, "#15803d"),
]

scores_carte = scores[~scores["Département"].isin(["La Réunion", "Martinique"])].copy()

fig = px.choropleth(
    scores_carte,
    geojson=geojson_departements,
    locations="Département",
    featureidkey="properties.nom",
    color="Score global personnalisé",
    color_continuous_scale=color_scale,
    range_color=(0, 1),
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
fig.update_layout(
    template="plotly_dark",
    height=680,
    margin={"l": 0, "r": 0, "t": 0, "b": 0},
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font={"color": "#e8edf2"},
    coloraxis_colorbar={
        "title": {"text": "Score", "font": {"color": "#e8edf2"}},
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
st.caption("Score 0–1 : plus proche de 1 = plus favorable selon les pondérations choisies.")

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

st.divider()
st.subheader("Sélection des départements")
departements_selectionnes = st.multiselect(
    "Sélectionne jusqu'à 4 départements",
    options=scores["Département"].tolist(),
    default=[],
    placeholder="Tape pour rechercher un département...",
)
if len(departements_selectionnes) > 4:
    departements_selectionnes = departements_selectionnes[:4]
    st.info("Comparaison limitée à 4 départements pour garder le radar lisible.")

filtered_df = scores[scores["Département"].isin(departements_selectionnes)] if departements_selectionnes else scores

st.subheader("Profil des critères par département")
st.caption("Échelle 0–1 : plus la valeur est proche de 1, plus le critère est favorable.")

selected_rows = []
for departement in departements_selectionnes:
    row = scores[scores["Département"] == departement]
    if not row.empty:
        selected_rows.append(row.iloc[0])

if not selected_rows:
    moyenne = {"Département": "Moyenne nationale"}
    for colonne in colonnes_selectionnees:
        moyenne[colonne] = scores[colonne].mean()
    selected_rows = [moyenne]

radar_labels = selection_themes
radar_labels_closed = radar_labels + [radar_labels[0]]
fig_radar = go.Figure()
palette = ["#22c55e", "#38bdf8", "#a855f7", "#f97316"]
for index, row in enumerate(selected_rows):
    values = [row[themes[theme]] for theme in selection_themes]
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

max_values = [scores[themes[theme]].max() for theme in selection_themes]
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
st.subheader("Classement des départements")
st.dataframe(
    filtered_df[
        ["Département", "Région"] + colonnes_selectionnees + ["Score global personnalisé"]
    ].style.format({col: "{:.2f}" for col in colonnes_selectionnees + ["Score global personnalisé"]}),
    use_container_width=True,
    hide_index=True,
)

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
