import streamlit as st
import pandas as pd
import plotly.express as px

# Titre généralisé
st.title("📈 Analyse des Séries Temporelles & Enregistreurs")
st.caption("Page dédiée à l'importation de données horodatées provenant d'enregistreurs, capteurs ou stations de mesure.")

# Configuration dans la barre latérale
with st.sidebar:
    st.header("⚙️ Configuration du fichier")
    skip_rows = st.number_input(
        "Lignes d'en-tête/métadonnées à ignorer", 
        min_value=0, 
        value=10, 
        step=1,
        help="Nombre de lignes d'en-tête à ignorer avant le tableau de données (0 si aucune)."
    )

uploaded_file = st.file_uploader(
    "Dépose ton fichier de données (Excel ou CSV)", 
    type=["xlsx", "xls", "csv"]
)

if uploaded_file is not None:
    try:
        # 1. LECTURE AVEC DÉTECTION AUTOMATIQUE DU SÉPARATEUR (;, ,, \t)
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, skiprows=skip_rows, sep=None, engine='python')
        else:
            df = pd.read_excel(uploaded_file, skiprows=skip_rows)

        # Nettoyage des colonnes et des lignes vides
        df = df.dropna(how="all", axis=1).dropna(how="all", axis=0).reset_index(drop=True)
        df.columns = [str(col).strip() for col in df.columns]
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]

        if len(df.columns) < 3:
            st.warning("⚠️ Moins de 3 colonnes séparées. Ajuste le nombre de lignes à ignorer dans la barre latérale.")
            st.write("Colonnes détectées :", df.columns.tolist())
        else:
            # 2. COMBINAISON DATE + HEURE
            col_date = df.columns[0]  # Première colonne (Date)
            col_time = df.columns[1]  # Deuxième colonne (Time)

            # Création de la colonne Horodatage
            df['Horodatage'] = pd.to_datetime(
                df[col_date].astype(str) + ' ' + df[col_time].astype(str),
                dayfirst=True,
                errors='coerce'
            )

            # Nettoyage et tri chronologique
            df_clean = df.dropna(subset=['Horodatage']).sort_values('Horodatage').copy()

            st.success(f"✅ Fichier chargé avec succès : **{len(df_clean)} enregistrements** analysés.")

            # 3. SÉLECTION DE LA MESURE À ANALYSER
            colonnes_mesures = [c for c in df_clean.columns if c not in [col_date, col_time, 'Horodatage']]
            col_y = st.selectbox("Sélectionne le paramètre à analyser :", options=colonnes_mesures)

            # 4. INDICATEURS CLÉS (METRICS)
            col1, col2, col3, col4 = st.columns(4)
            
            valeur_min = df_clean[col_y].min()
            valeur_max = df_clean[col_y].max()
            valeur_moy = df_clean[col_y].mean()

            col1.metric("Points enregistrés", f"{len(df_clean)}")
            col2.metric("Minimum", f"{valeur_min:.3f}")
            col3.metric("Maximum", f"{valeur_max:.3f}")
            col4.metric("Moyenne", f"{valeur_moy:.3f}")

            st.markdown("---")

            # 5. GRAPHIQUE TEMPOREL INTERACTIF
            st.subheader(f"📊 Évolution temporelle de : {col_y}")
            fig = px.line(
                df_clean, 
                x='Horodatage', 
                y=col_y, 
                labels={'Horodatage': 'Horodatage', col_y: col_y}
            )
            fig.update_layout(
                xaxis_rangeslider_visible=True,
                template="plotly_white"
            )
            st.plotly_chart(fig, use_container_width=True)

            # 6. TABLEAU DES DONNÉES
            with st.expander("🔍 Afficher le tableau de données complet"):
                st.dataframe(df_clean[['Horodatage', col_y] + [c for c in colonnes_mesures if c != col_y]], use_container_width=True)

    except Exception as e:
        st.error(f"Erreur lors du traitement du fichier : {e}")
