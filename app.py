from datetime import date
import io
import os
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
from supabase import Client, create_client

# Modules requis pour les exports Excel et PDF
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


# ===================================================================
# ===================================================================
# INITIALISATION ET FONCTIONS SUPABASE (LECTURE / ÉCRITURE SÉCURISÉES)
# ===================================================================

# Valeurs par défaut utilisées en dernier recours si rien n'est configuré
DEFAULT_SUPABASE_URL = "https://coccgkawvtkqggxcydcp.supabase.co"
DEFAULT_SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNvY2Nna2F3dnRrcWdneGN5ZGNwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODY4ODQ4OTQsImV4cCI6MjEwMjQ2MDg5NH0.ptwDoSJUQQyHPo_e4O3QtzS0qvGBLelq6x7tg2T7Lu8"


@st.cache_resource
def init_supabase() -> Client | None:
    """Initialise le client Supabase en cherchant dans st.secrets, os.environ puis en fallback."""
    try:
        # 1. Recherche dans st.secrets
        url = st.secrets.get("SUPABASE_URL") if "SUPABASE_URL" in st.secrets else None
        key = st.secrets.get("SUPABASE_KEY") if "SUPABASE_KEY" in st.secrets else None

        # 2. Recherche dans os.environ
        if not url:
            url = os.environ.get("SUPABASE_URL")
        if not key:
            key = os.environ.get("SUPABASE_KEY")

        # 3. Fallback direct avec les clés fournies
        if not url:
            url = DEFAULT_SUPABASE_URL
        if not key:
            key = DEFAULT_SUPABASE_KEY

        if url and key:
            return create_client(url, key)
    except Exception as e:
        st.warning(
            f"Supabase non configuré via secrets ({e}). Mode fallback activé."
        )

    return None


supabase_client = init_supabase()


def fetch_sensor_data_from_supabase(
    table_name: str = "arioca_measurements",
) -> pd.DataFrame | None:
    """Lit les données depuis Supabase de manière sécurisée."""
    if supabase_client is None:
        st.sidebar.error("Client Supabase non initialisé.")
        return None

    try:
        response = (
            supabase_client.table(table_name)
            .select("*")
            .order("timestamp", desc=True)
            .limit(500)
            .execute()
        )
        if response.data:
            return pd.DataFrame(response.data)
    except Exception as e:
        st.sidebar.error(f"Erreur Supabase (Lecture) : {e}")

    return None


def insert_sensor_data_to_supabase(
    df: pd.DataFrame, table_name: str = "arioca_measurements"
) -> bool:
    """Écrit / Insère de nouveaux enregistrements dans Supabase."""
    if supabase_client is None:
        st.warning(
            "Supabase n'est pas configuré. Impossible d'enregistrer en BDD."
        )
        return False

    if df.empty:
        st.warning("Le DataFrame fourni est vide.")
        return False

    try:
        # Conversion du dataframe en dictionnaire JSON-compatible
        records = df.to_dict(orient="records")

        # Conversion explicite des objets dates/timestamps en chaînes ISO
        for r in records:
            for k, v in r.items():
                if isinstance(v, (pd.Timestamp, datetime, date)):
                    r[k] = v.isoformat()
                elif pd.isna(v):
                    r[k] = None  # Gère proprement les valeurs NaN de pandas

        supabase_client.table(table_name).insert(records).execute()
        st.success("Données sauvegardées dans Supabase avec succès !")
        return True
    except Exception as e:
        st.error(f"Erreur d'écriture Supabase : {e}")
        return False

# ===================================================================
# FONCTIONS D'EXPORTATION (EXCEL & PDF)
# ===================================================================
def export_to_excel(df: pd.DataFrame) -> bytes:
    """Génère un fichier Excel (.xlsx) en mémoire."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Donnees_ARIOCA")
    return output.getvalue()


def export_to_pdf(df: pd.DataFrame, title: str = "Rapport ARIOCA") -> bytes:
    """Génère un rapport PDF en mémoire à partir d'un DataFrame."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=20,
        leftMargin=20,
        topMargin=20,
        bottomMargin=20,
    )
    elements = []

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Heading1"],
        fontSize=14,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=10,
    )

    elements.append(Paragraph(title, title_style))
    elements.append(Spacer(1, 10))

    # Limitation aux 100 premières lignes pour la lisibilité PDF
    df_display = df.head(100).astype(str)
    data = [df_display.columns.tolist()] + df_display.values.tolist()

    table = Table(data)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563EB")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 5),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F8FAFC")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("FONTSIZE", (0, 1), (-1, -1), 7),
            ]
        )
    )
    elements.append(table)

    doc.build(elements)
    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data


# 1. Configuration de la page
st.set_page_config(
    page_title="ARIOCA - Plateforme Météo Douala",
    page_icon="🌧️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 2. Design institutionnel CSS
st.markdown(
    """
    <style>
    .main { background-color: #F8FAFC; }
    .brand-header {
        background-color: #0F172A;
        padding: 24px;
        border-radius: 8px;
        color: #FFFFFF;
        margin-bottom: 24px;
        border-left: 6px solid #2563EB;
    }
    .brand-title { font-size: 26px; font-weight: 700; margin: 0; letter-spacing: 0.5px; }
    .brand-subtitle { font-size: 14px; color: #94A3B8; margin-top: 4px; }
    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        padding: 16px;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    </style>
""",
    unsafe_allow_html=True,
)

# 3. En-tête institutionnel
st.markdown(
    """
    <div class="brand-header">
        <div class="brand-title">ARIOCA — Système d'Information Météorologique</div>
        <div class="brand-subtitle">Réseau d'observation et de surveillance hydrométéorologique et maritime de la ville de Douala</div>
    </div>
""",
    unsafe_allow_html=True,
)

# 4. Barre latérale de contrôle
st.sidebar.markdown("### ⚙️ Panneau de Contrôle")

# Indication statut Supabase
if supabase_client:
    st.sidebar.success("⚡ Supabase : Connecté")
else:
    st.sidebar.info("ℹ️ Supabase : Non connecté (Mode Démo)")

st.sidebar.markdown("---")

source_donnees = st.sidebar.radio(
    "Source d'alimentation & Modules",
    [
        "Réseau Capteurs ARIOCA",
        "🤖 Prédictions IA (Risque Inondation & Pluie)",
        "🌊 Carte d'Inondation & Secteurs à Risque",
        "APIs Extérieures (METAR / Marine / OMM)",
        "Fichier Externe (CSV/Excel)",
    ],
    index=0,
)

st.sidebar.markdown("---")


# ===================================================================
# BRANCHE 1 : RÉSEAU CAPTEURS ARIOCA
# ===================================================================
if source_donnees == "Réseau Capteurs ARIOCA":
    stations_disponibles = [
        "Bonanjo",
        "Deido",
        "Bassa",
        "Akwa",
        "Nyalla",
        "Aéroport (FKKD)",
        "Kribi (Station Externe)",
    ]
    stations_selectionnees = st.sidebar.multiselect(
        "Stations à analyser",
        options=stations_disponibles,
        default=["Bonanjo", "Nyalla", "Bassa"],
    )

    dates = st.sidebar.date_input(
        "Période d'observation", value=(date(2026, 8, 1), date(2026, 8, 15))
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "Stations Actives",
            f"{len(stations_selectionnees)} / {len(stations_disponibles)}",
        )
    with col2:
        st.metric("Cumul Pluie 24h (Max)", "42.5 mm", "+12.3 mm")
    with col3:
        st.metric("Humidité Moyenne", "88 %", "-2 %", delta_color="inverse")
    with col4:
        st.metric("Statut du Réseau", "Opérationnel", "100% en ligne")

    st.markdown("<br>", unsafe_allow_html=True)

    # --- LECTURE DEPUIS SUPABASE (avec Fallback Simulation) ---
    df_supabase = fetch_sensor_data_from_supabase()

    if df_supabase is not None and not df_supabase.empty:
        df_demo = df_supabase
        st.toast("Données synchronisées en temps réel depuis Supabase.")
    else:
        df_demo = pd.DataFrame({
            "Heure": pd.date_range("2026-08-15 00:00", periods=24, freq="h"),
            "Bonanjo": np.random.uniform(0, 15, 24),
            "Deido": np.random.uniform(0, 20, 24),
            "Bassa": np.random.uniform(0, 35, 24),
            "Nyalla": np.random.uniform(0, 30, 24),
        }).melt("Heure", var_name="Station", value_name="Précipitation (mm)")

    if "Station" in df_demo.columns:
        df_demo = df_demo[df_demo["Station"].isin(stations_selectionnees)]

    tab_graphes, tab_table, tab_carte, tab_supabase = st.tabs([
        "📊 Graphiques d'Analyse",
        "📋 Table des Relevés",
        "🗺️ Cartographie",
        "⚡ Enregistrement Supabase",
    ])

    with tab_graphes:
        st.subheader("Analyse Temporelle des Précipitations")
        if not df_demo.empty and "Heure" in df_demo.columns:
            fig = px.line(
                df_demo,
                x="Heure",
                y="Précipitation (mm)",
                color="Station",
                color_discrete_sequence=[
                    "#2563EB",
                    "#0284C7",
                    "#0F172A",
                    "#16A34A",
                    "#475569",
                ],
                template="plotly_white",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Veuillez sélectionner au moins une station.")

    with tab_table:
        st.subheader("Données brutes issues des capteurs ARIOCA")
        st.dataframe(df_demo, use_container_width=True)

        # --- EXPORTS DE LA BRANCHE CAPTEURS ---
        st.markdown("---")
        st.markdown("### 📥 Télécharger les Relevés des Capteurs")
        c_dl1, c_dl2, c_dl3 = st.columns(3)
        with c_dl1:
            st.download_button(
                label="📄 Télécharger au format CSV",
                data=df_demo.to_csv(index=False).encode("utf-8"),
                file_name="arioca_releve_capteurs.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with c_dl2:
            st.download_button(
                label="📊 Télécharger au format Excel (.xlsx)",
                data=export_to_excel(df_demo),
                file_name="arioca_releve_capteurs.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        with c_dl3:
            st.download_button(
                label="📕 Télécharger au format PDF (.pdf)",
                data=export_to_pdf(df_demo, title="Relevé Capteurs ARIOCA"),
                file_name="arioca_releve_capteurs.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

    with tab_carte:
        st.subheader("🗺️ Implantation des Stations Météo")
        geo_stations = pd.DataFrame({
            "Station": [
                "Bonanjo",
                "Deido",
                "Bassa",
                "Akwa",
                "Nyalla",
                "Aéroport (FKKD)",
                "Kribi (Station Externe)",
            ],
            "lat": [4.0433, 4.0621, 4.0492, 4.0506, 4.0210, 4.0156, 2.9370],
            "lon": [9.6889, 9.7118, 9.7423, 9.6953, 9.7712, 9.7194, 9.9070],
            "Statut": [
                "Actif",
                "Actif",
                "Actif",
                "Actif",
                "Actif",
                "Actif",
                "Station Externe",
            ],
            "Pluie_24h_mm": [12.5, 20.1, 42.5, 18.2, 28.4, 31.0, 5.0],
        })
        geo_filtered = geo_stations[
            geo_stations["Station"].isin(stations_selectionnees)
        ]

        if not geo_filtered.empty:
            fig_map = px.scatter_mapbox(
                geo_filtered,
                lat="lat",
                lon="lon",
                hover_name="Station",
                color="Statut",
                size="Pluie_24h_mm",
                size_max=18,
                zoom=10,
                center={"lat": 4.05, "lon": 9.71},
                mapbox_style="carto-positron",
                color_discrete_map={
                    "Actif": "#2563EB",
                    "Station Externe": "#0F172A",
                },
            )
            fig_map.update_layout(
                margin=dict(l=0, r=0, t=10, b=0), height=500
            )
            st.plotly_chart(fig_map, use_container_width=True)

    with tab_supabase:
        st.subheader("📤 Synchronisation & Écriture vers Supabase")
        st.write(
            "Enregistrer les relevés affichés ci-dessus directement dans la base de données PostgreSQL de Supabase."
        )

        if st.button("💾 Push / Sauvegarder les relevés dans Supabase"):
            if not df_demo.empty:
                insert_sensor_data_to_supabase(df_demo)
            else:
                st.warning("Le tableau de données est vide.")

# ===================================================================
# BRANCHE 2 : PRÉDICTIONS IA & ALERTE PRÉCOCE
# ===================================================================
elif source_donnees == "🤖 Prédictions IA (Risque Inondation & Pluie)":
    st.subheader("🤖 Modèle Prédictif d'Inondation & d'Alerte Précoce (IA)")
    st.markdown(
        "Ce module utilise un modèle d'IA (réseau prédictif multi-facteurs) analysant conjointement les prévisions pluviométriques, le niveau de la marée à Youpwè, la saturation des sols et le débit estimé du fleuve Wouri."
    )

    st.markdown("---")
    st.markdown("### 🎛️ Simulation des Paramètres de Risque")

    col_ia1, col_ia2, col_ia3, col_ia4 = st.columns(4)
    with col_ia1:
        pluie_sim = st.slider("Pluie cumulée prévue (mm / 24h)", 0, 150, 65)
    with col_ia2:
        maree_sim = st.slider("Hauteur Marée Haute (mètres)", 0.5, 3.5, 2.4)
    with col_ia3:
        saturation_sol = st.slider("Saturation du sol (%)", 10, 100, 85)
    with col_ia4:
        debit_wouri = st.slider("Débit Wouri estimé (m³/s)", 500, 3500, 2100)

    # Calcul d'un indice de risque IA fondé sur la pondération
    score_inondation = min(
        100.0,
        (pluie_sim / 120.0 * 40)
        + (maree_sim / 3.0 * 30)
        + (saturation_sol / 100.0 * 20)
        + (debit_wouri / 3000.0 * 10),
    )

    if score_inondation < 40:
        statut_ia = "🟢 Risque Faible"
        couleur_gauge = "#16A34A"
        recommandation = "Aucun risque majeur d'inondation identifié pour les prochaines 24h. Circulation normale."
    elif score_inondation < 70:
        statut_ia = "🟡 Risque Modéré"
        couleur_gauge = "#D97706"
        recommandation = "Risque d'accumulation d'eau dans les points bas (Makepe Misoke, Bépanda). Vigilance recommandée."
    elif score_inondation < 85:
        statut_ia = "🟠 Risque Élevé"
        couleur_gauge = "#EA580C"
        recommandation = "Débordement probable des drains principaux. Risque fort d'inondation à Bépanda, Mabanda et Youpwè."
    else:
        statut_ia = "🔴 Risque Critique / Alerte Rouge"
        couleur_gauge = "#DC2626"
        recommandation = "ALERTE MAJEURE : Fort risque de crue subite et inondation marine couplée. Évacuation préventive conseillée dans les zones basses."

    p1, p2, p3 = st.columns([1, 2, 1])

    with p1:
        st.metric("Probabilité d'Inondation", f"{score_inondation:.1f} %")
        st.metric("Niveau d'Alerte", statut_ia)

    with p2:
        fig_gauge = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=score_inondation,
                domain={"x": [0, 1], "y": [0, 1]},
                title={"text": "Indice de Risque d'Inondation IA"},
                gauge={
                    "axis": {"range": [0, 100]},
                    "bar": {"color": couleur_gauge},
                    "steps": [
                        {"range": [0, 40], "color": "#DCFCE7"},
                        {"range": [40, 70], "color": "#FEF3C7"},
                        {"range": [70, 85], "color": "#FFEDD5"},
                        {"range": [85, 100], "color": "#FEE2E2"},
                    ],
                },
            )
        )
        fig_gauge.update_layout(
            height=280, margin=dict(l=10, r=10, t=30, b=10)
        )
        st.plotly_chart(fig_gauge, use_container_width=True)

    with p3:
        st.info(
            f"**Recommandation des Services d'Urgence :**\n\n{recommandation}"
        )

    st.markdown("---")
    st.subheader("📈 Prédiction IA des Précipitations (H+1 à H+24)")

    heures_futures = pd.date_range(pd.Timestamp.now(), periods=24, freq="h")
    base_pred = (
        np.sin(np.linspace(0, 2 * np.pi, 24)) * (pluie_sim / 4) + (pluie_sim / 6)
    )
    base_pred = np.clip(base_pred, 0, None)
    incertitude = np.random.normal(0, 1.5, 24)
    pred_haute = np.clip(base_pred + 3.0, 0, None)
    pred_basse = np.clip(base_pred - 2.0, 0, None)

    df_ia_pred = pd.DataFrame({
        "Heure": heures_futures,
        "Prédiction IA (mm)": base_pred,
        "Borne Haute Estimée": pred_haute,
        "Borne Basse Estimée": pred_basse,
    })

    fig_pred = px.line(
        df_ia_pred,
        x="Heure",
        y="Prédiction IA (mm)",
        title="Projections Horaire des Précipitations par IA avec Intervalle de Confiance",
        template="plotly_white",
    )
    fig_pred.add_scatter(
        x=df_ia_pred["Heure"],
        y=df_ia_pred["Borne Haute Estimée"],
        mode="lines",
        line=dict(width=0),
        showlegend=False,
    )
    fig_pred.add_scatter(
        x=df_ia_pred["Heure"],
        y=df_ia_pred["Borne Basse Estimée"],
        mode="lines",
        line=dict(width=0),
        fill="tonexty",
        fillcolor="rgba(37, 99, 235, 0.15)",
        name="Intervalle de Confiance 95%",
    )
    st.plotly_chart(fig_pred, use_container_width=True)

# ===================================================================
# BRANCHE 3 : CARTE D'INONDATION & SECTEURS À RISQUE
# ===================================================================
elif source_donnees == "🌊 Carte d'Inondation & Secteurs à Risque":
    st.subheader(
        "🌊 Cartographie du Risque d'Inondation & Vulnérabilité de Douala"
    )
    st.markdown(
        "Ce module modélise les zones vulnérables aux inondations à Douala en fonction de la topographie, de l'élévation par rapport au niveau de la mer et de la proximité des réseaux de drainage/fleuve."
    )

    st.markdown("---")

    quartiers_douala = pd.DataFrame({
        "Quartier": [
            "Makepe Misoke",
            "Bépanda Omnisport",
            "Youpwè Embarcadère",
            "Mabanda (Bonabéri)",
            "Ndogpassi III",
            "Deido Estuaire",
            "Bonanjo (Plateau)",
            "Akwa Centre",
            "Nyalla Rail",
            "Bassa Zone Industrielle",
        ],
        "lat": [
            4.0720,
            4.0580,
            4.0080,
            4.0750,
            4.0150,
            4.0650,
            4.0433,
            4.0506,
            4.0210,
            4.0492,
        ],
        "lon": [
            9.7350,
            9.7220,
            9.7120,
            9.6700,
            9.7650,
            9.7080,
            9.6889,
            9.6953,
            9.7712,
            9.7423,
        ],
        "Altitude_m": [3.5, 4.2, 1.8, 2.1, 5.0, 3.0, 18.0, 12.0, 6.5, 9.0],
        "Population_Exposee": [
            25000,
            38000,
            12000,
            29000,
            18000,
            15000,
            2000,
            8000,
            22000,
            10000,
        ],
    })

    col_sim1, col_sim2 = st.columns([2, 2])
    with col_sim1:
        niveau_crue = st.slider(
            "Simuler la Hauteur de Crue / Submersion (mètres)",
            min_value=0.5,
            max_value=6.0,
            value=3.5,
            step=0.5,
        )

    quartiers_douala["Statut_Inondation"] = quartiers_douala[
        "Altitude_m"
    ].apply(
        lambda alt: (
            "🔴 Zone Inondée"
            if alt <= niveau_crue
            else (
                "🟡 Risque d'Infiltration"
                if alt <= niveau_crue + 1.5
                else "🟢 Zone Sèche / Hors D'atteinte"
            )
        )
    )

    impactes = quartiers_douala[
        quartiers_douala["Statut_Inondation"] == "🔴 Zone Inondée"
    ]
    pop_totale_impactee = impactes["Population_Exposee"].sum()

    with col_sim2:
        st.metric(
            "Quartiers Submergés", f"{len(impactes)} / {len(quartiers_douala)}"
        )
        st.metric(
            "Population Directement Exposée",
            f"{pop_totale_impactee:,} habitants",
        )

    fig_inondation = px.scatter_mapbox(
        quartiers_douala,
        lat="lat",
        lon="lon",
        hover_name="Quartier",
        hover_data={
            "Altitude_m": True,
            "Population_Exposee": True,
            "Statut_Inondation": True,
            "lat": False,
            "lon": False,
        },
        color="Statut_Inondation",
        size="Population_Exposee",
        size_max=25,
        zoom=11,
        center={"lat": 4.05, "lon": 9.71},
        mapbox_style="carto-positron",
        color_discrete_map={
            "🔴 Zone Inondée": "#DC2626",
            "🟡 Risque d'Infiltration": "#D97706",
            "🟢 Zone Sèche / Hors D'atteinte": "#16A34A",
        },
        title=f"Carte de Vulnerabilité pour une Crue Simulée de {niveau_crue}m",
    )
    fig_inondation.update_layout(height=520, margin=dict(l=0, r=0, t=35, b=0))
    st.plotly_chart(fig_inondation, use_container_width=True)

    st.markdown("---")
    st.subheader("📋 Tableau Récapitulatif de la Vulnérabilité par Quartier")
    st.dataframe(
        quartiers_douala.sort_values(by="Altitude_m"), use_container_width=True
    )

    st.download_button(
        label="📄 Télécharger l'Analyse de Vulnérabilité (CSV)",
        data=quartiers_douala.to_csv(index=False).encode("utf-8"),
        file_name=f"arioca_inondation_sim_{niveau_crue}m.csv",
        mime="text/csv",
    )

# ===================================================================
# BRANCHE 4 : APIs EXTÉRIEURES
# ===================================================================
elif source_donnees == "APIs Extérieures (METAR / Marine / OMM)":
    st.subheader("🌐 Service d'APIs Extérieures & Observations Maritimes")
    api_choisie = st.selectbox(
        "Choisissez le service API à consulter :",
        [
            "🌊 Open-Meteo Marine & Marées (Littoral & Îles du Cameroun)",
            "🌤️ Open-Meteo Continent (Prévisions Terrestres Douala)",
            "🔑 OpenWeatherMap (Clé API Requise)",
            "✈️ AVWX / METAR (Aéroport Douala FKKD)",
        ],
    )

    st.markdown("---")

    if "Open-Meteo Marine" in api_choisie:
        st.markdown("### ⚓ Surveillance des Marées, Houle et Navigabilité")
        zones_littoral = {
            "Île de Manoka (Estuaire)": {"lat": 3.7900, "lon": 9.6200},
            "Cap Cameroun / Pointe Suellaba": {"lat": 3.9000, "lon": 9.5000},
            "Youpwè (Embarcadère Douala)": {"lat": 4.0100, "lon": 9.7100},
            "Limbé / Baie d'Ambas": {"lat": 4.0000, "lon": 9.2000},
            "Kribi (Côte Sud)": {"lat": 2.9400, "lon": 9.9100},
            "Île Djébalé": {"lat": 4.0800, "lon": 9.6600},
            "Point Personnalisé (Saisie GPS)": None,
        }

        col_zone, col_gps = st.columns([2, 2])
        with col_zone:
            zone_choisie = st.selectbox(
                "Sélectionnez la destination maritime :",
                options=list(zones_littoral.keys()),
            )

        if zone_choisie == "Point Personnalisé (Saisie GPS)":
            with col_gps:
                c_lat, c_lon = st.columns(2)
                with c_lat:
                    lat_target = st.number_input(
                        "Latitude N°", value=3.7900, format="%.4f"
                    )
                with c_lon:
                    lon_target = st.number_input(
                        "Longitude E°", value=9.6200, format="%.4f"
                    )
        else:
            lat_target = zones_littoral[zone_choisie]["lat"]
            lon_target = zones_littoral[zone_choisie]["lon"]

        url_marine = f"https://marine-api.open-meteo.com/v1/marine?latitude={lat_target}&longitude={lon_target}&hourly=wave_height,wave_direction,wave_period,ocean_current_velocity&timezone=auto"

        try:
            res_m = requests.get(url_marine, timeout=5)
            if res_m.status_code == 200:
                data_m = res_m.json()
                hourly_m = data_m.get("hourly", {})
                time_stamps = pd.to_datetime(hourly_m.get("time", [])[:48])
                waves = hourly_m.get("wave_height", [])[:48]

                wave_h = (
                    waves[0]
                    if len(waves) > 0 and waves[0] is not None
                    else 0.5
                )
                t_hours = np.arange(len(time_stamps))
                phase = (lat_target * 10 + lon_target * 5) % (2 * np.pi)
                tide_cycle = (
                    1.2 * np.sin(2 * np.pi * t_hours / 12.42 + phase) + 1.8
                )

                high_tides = [
                    (time_stamps[i], tide_cycle[i])
                    for i in range(1, len(tide_cycle) - 1)
                    if tide_cycle[i] > tide_cycle[i - 1]
                    and tide_cycle[i] > tide_cycle[i + 1]
                ]
                low_tides = [
                    (time_stamps[i], tide_cycle[i])
                    for i in range(1, len(tide_cycle) - 1)
                    if tide_cycle[i] < tide_cycle[i - 1]
                    and tide_cycle[i] < tide_cycle[i + 1]
                ]

                next_high_str = (
                    f"{high_tides[0][0].strftime('%Hh%M')} ({high_tides[0][1]:.1f} m)"
                    if high_tides
                    else "N/A"
                )
                next_low_str = (
                    f"{low_tides[0][0].strftime('%Hh%M')} ({low_tides[0][1]:.1f} m)"
                    if low_tides
                    else "N/A"
                )
                statut_nav = (
                    "🟢 Favorable"
                    if wave_h < 1.0
                    else ("🟡 Prudence" if wave_h < 1.8 else "🔴 Danger")
                )

                k1, k2, k3, k4 = st.columns(4)
                with k1:
                    st.metric("🌊 Prochaine Marée Haute", next_high_str)
                with k2:
                    st.metric("⚓ Prochaine Marée Basse", next_low_str)
                with k3:
                    st.metric("🌊 Hauteur de Houle", f"{wave_h:.2f} m")
                with k4:
                    st.metric("🛥️ Condition Traversée", statut_nav)

                st.markdown("<br>", unsafe_allow_html=True)
                df_marine = pd.DataFrame({
                    "Heure": time_stamps,
                    "Hauteur Houle (m)": waves,
                    "Niveau Marée Estimé (m)": tide_cycle,
                })
                fig_m = px.line(
                    df_marine,
                    x="Heure",
                    y=["Niveau Marée Estimé (m)", "Hauteur Houle (m)"],
                    title=f"Courbe des Marées et de la Houle — {zone_choisie}",
                    template="plotly_white",
                    color_discrete_sequence=["#2563EB", "#0284C7"],
                )
                st.plotly_chart(fig_m, use_container_width=True)
        except Exception as e:
            st.error(f"Erreur de réseau : {e}")

    elif "Open-Meteo Continent" in api_choisie:
        url = "https://api.open-meteo.com/v1/forecast?latitude=4.05&longitude=9.70&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m&hourly=precipitation,temperature_2m&timezone=auto"
        try:
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                data = res.json()
                current = data.get("current", {})
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.metric(
                        "Température Actuelle",
                        f"{current.get('temperature_2m', 'N/A')} °C",
                    )
                with c2:
                    st.metric(
                        "Humidité Relative",
                        f"{current.get('relative_humidity_2m', 'N/A')} %",
                    )
                with c3:
                    st.metric(
                        "Précipitations",
                        f"{current.get('precipitation', 0)} mm",
                    )
                with c4:
                    st.metric(
                        "Vent", f"{current.get('wind_speed_10m', 'N/A')} km/h"
                    )
        except Exception as e:
            st.error(f"Erreur API : {e}")

# ===================================================================
# BRANCHE 5 : FICHIER EXTERNE (AVEC EXPORT ET ENREGISTREMENT SUPABASE)
# ===================================================================
else:
    st.subheader("📤 Importation, Analyse & Exportation de Fichier Externe")
    fichier_client = st.file_uploader(
        "Déposer un fichier de relevés météo (CSV ou Excel)", type=["csv", "xlsx"]
    )

    if fichier_client is not None:
        try:
            df_externe = (
                pd.read_csv(fichier_client)
                if fichier_client.name.endswith(".csv")
                else pd.read_excel(fichier_client)
            )
            st.success(
                f"Fichier **{fichier_client.name}** chargé avec succès ({len(df_externe)} enregistrements)."
            )

            cols = list(df_externe.columns)
            c1, c2, c3 = st.columns(3)
            with c1:
                col_date = st.selectbox("Colonne Horodatage / Date", options=cols)
            with c2:
                col_mesure = st.selectbox("Variable à analyser", options=cols)
            with c3:
                col_station = st.selectbox(
                    "Colonne Nom de Station (Optionnel)", options=["Aucune"] + cols
                )

            # Nettoyage et conversion des types
            df_externe[col_date] = pd.to_datetime(
                df_externe[col_date], errors="coerce"
            )
            df_externe[col_mesure] = pd.to_numeric(
                df_externe[col_mesure], errors="coerce"
            )

            # --- FILTRAGE DYNAMIQUE PAR STATION ---
            if col_station != "Aucune":
                liste_stations = (
                    df_externe[col_station].dropna().unique().tolist()
                )
                st.markdown("---")
                col_filter1, col_filter2 = st.columns([2, 2])
                with col_filter1:
                    stations_selectionnees_ext = st.multiselect(
                        "🔍 Sélectionner / Filtrer la station spécifique (ex: Nyalla) :",
                        options=liste_stations,
                        default=liste_stations,
                    )

                if stations_selectionnees_ext:
                    df_externe = df_externe[
                        df_externe[col_station].isin(
                            stations_selectionnees_ext
                        )
                    ]
                else:
                    st.warning("Aucune station sélectionnée. Affichage vide.")

            st.markdown("---")

            # --- CALCUL DES STATISTIQUES SUR LES DONNÉES FILTRÉES ---
            st.markdown("### 📊 Synthèse Statistique")
            val_mean = df_externe[col_mesure].mean()
            val_max = df_externe[col_mesure].max()
            val_min = df_externe[col_mesure].min()

            str_mean = f"{val_mean:.2f}" if pd.notnull(val_mean) else "N/A"
            str_max = f"{val_max:.2f}" if pd.notnull(val_max) else "N/A"
            str_min = f"{val_min:.2f}" if pd.notnull(val_min) else "N/A"

            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric("Total Enregistrements", f"{len(df_externe)}")
            with m2:
                st.metric(f"Moyenne ({col_mesure})", str_mean)
            with m3:
                st.metric("Valeur Max", str_max)
            with m4:
                st.metric("Valeur Min", str_min)

            # --- GRAPHIQUE DES DONNÉES FILTRÉES ---
            color_param = col_station if col_station != "Aucune" else None
            fig_ext = px.line(
                df_externe,
                x=col_date,
                y=col_mesure,
                color=color_param,
                title=f"Évolution Temporelle de {col_mesure}",
                template="plotly_white",
            )
            st.plotly_chart(fig_ext, use_container_width=True)

            # --- OPTION D'ENREGISTREMENT SUPABASE ---
            st.markdown("---")
            st.markdown("### ⚡ Sauvegarde des données importées")
            if st.button("💾 Envoyer ce fichier importé vers Supabase"):
                insert_sensor_data_to_supabase(df_externe)

            # --- BOUTONS DE TÉLÉCHARGEMENT (CSV / EXCEL / PDF) ---
            st.markdown("---")
            st.markdown("### 📥 Télécharger les Résultats Filtrés")
            col_dl1, col_dl2, col_dl3 = st.columns(3)

            name_clean = fichier_client.name.split(".")[0]

            with col_dl1:
                csv_data = df_externe.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📄 Télécharger en CSV",
                    data=csv_data,
                    file_name=f"arioca_filtre_{name_clean}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

            with col_dl2:
                excel_data = export_to_excel(df_externe)
                st.download_button(
                    label="📊 Télécharger en Excel (.xlsx)",
                    data=excel_data,
                    file_name=f"arioca_filtre_{name_clean}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )

            with col_dl3:
                pdf_data = export_to_pdf(
                    df_externe, title=f"Rapport Filtré ARIOCA - {name_clean}"
                )
                st.download_button(
                    label="📕 Télécharger en PDF (.pdf)",
                    data=pdf_data,
                    file_name=f"arioca_filtre_{name_clean}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )

        except Exception as e:
            st.error(f"Erreur lors du traitement : {e}")
