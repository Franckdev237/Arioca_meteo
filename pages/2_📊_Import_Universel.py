import streamlit as st
import pandas as pd
import plotly.express as px

# Titre et présentation
st.title("📊 Importation & Analyse Universelle")
st.caption("Charge n'importe quel fichier Excel ou CSV standard pour l'analyser, créer des graphiques personnalisés et explorer les statistiques.")

# Zone de dépôt de fichier
uploaded_file = st.file_uploader(
    "Dépose ton fichier (Excel .xlsx, .xls ou CSV)", 
    type=["xlsx", "xls", "csv"]
)

if uploaded_file is not None:
    try:
        # 1. LECTURE INTELLIGENTE DU FICHIER
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, sep=None, engine='python')
        else:
            df = pd.read_excel(uploaded_file)

        # Nettoyage des lignes et colonnes entièrement vides
        df = df.dropna(how="all", axis=1).dropna(how="all", axis=0).reset_index(drop=True)
        df.columns = [str(col).strip() for col in df.columns]

        st.success(f"✅ Fichier **{uploaded_file.name}** chargé avec succès !")

        # 2. INDICATEURS RAPIDES (KPIs)
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Lignes", f"{df.shape[0]:,}")
        col2.metric("Colonnes", f"{df.shape[1]}")
        col3.metric("Colonnes numériques", f"{len(df.select_dtypes(include=['number']).columns)}")
        col4.metric("Valeurs manquantes", f"{df.isna().sum().sum():,}")

        st.markdown("---")

        # 3. ONGLETS D'ANALYSE
        tab_graph, tab_stats, tab_data = st.tabs(["📈 Graphique Personnalisé", "📋 Statistiques", "🔍 Exploration des Données"])

        # --- ONGLET 1 : GRAPHIQUE INTERACTIF ---
        with tab_graph:
            st.subheader("Générateur de Graphique")
            
            c1, c2, c3 = st.columns(3)
            
            with c1:
                type_chart = st.selectbox(
                    "Type de graphique :",
                    ["Courbe (Ligne)", "Barres", "Nuage de points (Scatter)", "Histogramme", "Boîte à moustaches (Box)"]
                )
            
            with c2:
                col_x = st.selectbox("Axe X (Horizontale) :", options=df.columns)
            
            with c3:
                # Proposer 'Aucune' pour les histogrammes ou boîtes à moustaches
                options_y = list(df.columns)
                col_y = st.selectbox("Axe Y (Verticale) :", options=options_y, index=min(1, len(options_y)-1))

            # Option avancée : Couleur / Groupement
            col_color = st.selectbox("Grouper/Colorer par (Optionnel) :", options=["Aucun"] + list(df.columns))
            color_param = col_color if col_color != "Aucun" else None

            # Génération du graphique Plotly selon le choix
            try:
                if type_chart == "Courbe (Ligne)":
                    fig = px.line(df, x=col_x, y=col_y, color=color_param, title=f"{col_y} en fonction de {col_x}")
                elif type_chart == "Barres":
                    fig = px.bar(df, x=col_x, y=col_y, color=color_param, title=f"{col_y} par {col_x}")
                elif type_chart == "Nuage de points (Scatter)":
                    fig = px.scatter(df, x=col_x, y=col_y, color=color_param, title=f"Relation entre {col_x} et {col_y}")
                elif type_chart == "Histogramme":
                    fig = px.histogram(df, x=col_x, color=color_param, title=f"Distribution de {col_x}")
                elif type_chart == "Boîte à moustaches (Box)":
                    fig = px.box(df, x=col_x, y=col_y, color=color_param, title=f"Distribution de {col_y} par {col_x}")

                fig.update_layout(template="plotly_white")
                st.plotly_chart(fig, use_container_width=True)

            except Exception as chart_err:
                st.error(f"Impossible de générer ce type de graphique avec les colonnes sélectionnées : {chart_err}")

        # --- ONGLET 2 : STATISTIQUES ---
        with tab_stats:
            st.subheader("Résumé Statistique")
            
            col_num, col_cat = st.columns(2)
            
            with col_num:
                st.markdown("**Variables Numériques :**")
                df_num = df.select_dtypes(include=['number'])
                if not df_num.empty:
                    st.dataframe(df_num.describe().T, use_container_width=True)
                else:
                    st.info("Aucune colonne numérique détectée.")

            with col_cat:
                st.markdown("**Types de données & Valeurs Manquantes :**")
                info_df = pd.DataFrame({
                    "Type": df.dtypes.astype(str),
                    "Valeurs Nulles": df.isna().sum(),
                    "% Nuls": (df.isna().sum() / len(df) * 100).round(2)
                })
                st.dataframe(info_df, use_container_width=True)

        # --- ONGLET 3 : EXPLORATION DU TABLEAU ---
        with tab_data:
            st.subheader("Aperçu interactif des données")
            
            # Filtre de recherche dans le tableau
            search = st.text_input("🔍 Rechercher un mot-clé dans les données :", "")
            
            if search:
                mask = df.astype(str).apply(lambda row: row.str.contains(search, case=False).any(), axis=1)
                df_filtered = df[mask]
                st.caption(f"{len(df_filtered)} ligne(s) trouvée(s).")
                st.dataframe(df_filtered, use_container_width=True)
            else:
                st.dataframe(df, use_container_width=True)

    except Exception as e:
        st.error(f"Erreur lors de la lecture du fichier : {e}")
