import pandas as pd
import plotly.express as px
import streamlit as st

from utils.excel_helpers import (
    ajouter_surlignage_departements,
    charger_csv,
    charger_geojson,
    get_global_department_selection,
    render_global_department_selector,
    styliser_carte_departements,
)
from utils.ui_theme import apply_horizon_theme

apply_horizon_theme()
st.title("Criminalité projetée par département")
render_global_department_selector(
    caption="La sélection est partagée entre les pages. Les départements choisis sont surlignés sur la carte et filtrent les graphiques."
)

df = charger_csv("pages/tables/CrimebyDept_2040.csv")
geojson_departements = charger_geojson("pages/tables/departements.geojson")

df.columns = [str(col).strip() for col in df.columns]
if "Coefficient" in df.columns and "coefficient" not in df.columns:
    df = df.rename(columns={"Coefficient": "coefficient"})
if "taux_pour_mille_2040" not in df.columns:
    df["taux_pour_mille_2040"] = pd.NA

df["num_dep"] = df["num_dep"].astype(str).str.zfill(2)
df["nombre"] = pd.to_numeric(df["nombre"], errors="coerce")
df["coefficient"] = pd.to_numeric(df["coefficient"], errors="coerce")
df["taux_pour_mille_2040"] = pd.to_numeric(df["taux_pour_mille_2040"], errors="coerce")
# Un coefficient élevé correspond ici à un territoire plus sûr.
df["Indice sécurité"] = df["coefficient"].round(2)
df["Crimes pour 1000 habitants"] = df["taux_pour_mille_2040"] * 1000
departements_selectionnes = get_global_department_selection(df["dep_name"].dropna().unique())
df_scope = df[df["dep_name"].isin(departements_selectionnes)].copy() if departements_selectionnes else df.copy()

crime_scale = ["#fff3bf", "#ffb84d", "#f97316", "#d9480f", "#7f1d1d"]
security_scale = ["#991b1b", "#dc2626", "#f59e0b", "#84cc16", "#15803d"]

has_rate = df["Crimes pour 1000 habitants"].notna().any()
indicateurs = {
    "Indice sécurité": "Indice sécurité",
    "Nombre de crimes projetés": "nombre",
}
if has_rate:
    indicateurs["Crimes pour 1000 habitants"] = "Crimes pour 1000 habitants"

indicateur = st.selectbox("Indicateur affiché sur la carte", list(indicateurs.keys()))
colonne_carte = indicateurs[indicateur]

col1, col2, col3 = st.columns(3)
col1.metric("Indice sécurité moyen", f"{df_scope['Indice sécurité'].mean():.2f}".replace(".", ","))
col2.metric("Crimes projetés moyens", f"{round(df_scope['nombre'].mean()):,.0f}")
col3.metric(
    "Département le plus sûr",
    df_scope.sort_values("Indice sécurité", ascending=False).iloc[0]["dep_name"],
)

custom_data = ["num_dep", "nombre", "Indice sécurité"]
if has_rate:
    custom_data.append("Crimes pour 1000 habitants")

fig_carte = px.choropleth(
    df,
    geojson=geojson_departements,
    locations="dep_name",
    featureidkey="properties.nom",
    color=colonne_carte,
    hover_name="dep_name",
    custom_data=custom_data,
    color_continuous_scale=security_scale if colonne_carte == "Indice sécurité" else crime_scale,
    labels={
        "nombre": "Crimes projetés",
        "Crimes pour 1000 habitants": "Crimes pour 1000 hab.",
        "Indice sécurité": "Indice sécurité",
    },
)
hover_template = (
    "<b>%{hovertext}</b><br>"
    "Code département: %{customdata[0]}<br>"
    "Crimes projetés: %{customdata[1]:,.0f}<br>"
    "Indice sécurité: %{customdata[2]:.2f}"
)
if has_rate:
    hover_template += "<br>Crimes pour 1000 hab.: %{customdata[3]:.1f}"
hover_template += "<extra></extra>"

fig_carte = styliser_carte_departements(
    fig_carte,
    "Indice sécurité" if colonne_carte == "Indice sécurité" else "Crimes projetés",
    height=760,
    hovertemplate=hover_template,
    tickformat=".2f" if colonne_carte == "Indice sécurité" else ",.0f",
    marker_line_color="#7a8395",
    marker_line_width=1.15,
    colorbar_thickness=18,
)
fig_carte = ajouter_surlignage_departements(
    fig_carte,
    geojson_departements,
    departements_selectionnes,
    "properties.nom",
)
st.plotly_chart(fig_carte, use_container_width=True)

gauche, droite = st.columns(2)

top_crimes = df_scope.sort_values("nombre", ascending=False).head(15)
fig_top = px.bar(
    top_crimes,
    x="nombre",
    y="dep_name",
    orientation="h",
    color="nombre",
    title="Départements les plus exposés en volume de crimes projetés",
    labels={"dep_name": "Département", "nombre": "Crimes projetés"},
    color_continuous_scale=crime_scale,
)
fig_top.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
)
fig_top.update_yaxes(categoryorder="total ascending")
fig_top.update_traces(
    hovertemplate="<b>%{y}</b><br>Crimes projetés: %{x:,.0f}<extra></extra>"
)
gauche.plotly_chart(fig_top, use_container_width=True)

top_safe = df_scope.sort_values("Indice sécurité", ascending=False).head(15)
fig_safe = px.bar(
    top_safe,
    x="Indice sécurité",
    y="dep_name",
    orientation="h",
    color="Indice sécurité",
    title="Départements les plus sûrs selon l'indice sécurité",
    labels={"dep_name": "Département", "Indice sécurité": "Indice sécurité"},
    color_continuous_scale=security_scale,
)
fig_safe.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
)
fig_safe.update_yaxes(categoryorder="total ascending")
fig_safe.update_traces(
    hovertemplate="<b>%{y}</b><br>Indice sécurité: %{x:.2f}<extra></extra>"
)
droite.plotly_chart(fig_safe, use_container_width=True)

fig_scatter = px.scatter(
    df_scope.sort_values("Indice sécurité"),
    x="Crimes pour 1000 habitants" if has_rate else "Indice sécurité",
    y="nombre",
    hover_name="dep_name",
    text="num_dep",
    title="Indice sécurité et volume de crimes projetés",
    labels={
        "nombre": "Crimes projetés",
        "Indice sécurité": "Indice sécurité",
        "Crimes pour 1000 habitants": "Crimes pour 1000 hab.",
    },
    color="Indice sécurité",
    color_continuous_scale=security_scale,
)
fig_scatter.update_traces(textposition="top center")
fig_scatter.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
)
st.plotly_chart(fig_scatter, use_container_width=True)

with st.expander("Voir les données"):
    st.dataframe(
        df_scope.sort_values("Indice sécurité", ascending=False).style.format(
            {
                "nombre": "{:,.0f}",
                "Crimes pour 1000 habitants": "{:.1f}",
                "Indice sécurité": "{:.2f}",
            }
        ),
        use_container_width=True,
    )
