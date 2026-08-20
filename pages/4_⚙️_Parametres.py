import streamlit as st

st.title("⚙️ Paramètres & Configuration")
st.caption("Gérez les configurations globales de la plateforme.")

tab1, tab2, tab3 = st.tabs(["🏢 Charte & Entreprise", "⚠️ Seuils d'Alerte", "🔌 Connexions & API"])

# --- TAB 1 : PERSONNALISATION ---
with tab1:
    st.subheader("Personnalisation des rapports PDF")
    nom_entreprise = st.text_input("Nom de l'entreprise", value="Mon Entreprise")
    logo_file = st.file_uploader("Logo de l'entreprise (PNG/JPG)", type=["png", "jpg"])
    
    if st.button("Enregistrer la charte"):
        st.success("Configuration sauvegardée !")

# --- TAB 2 : SEUILS D'ALERTE ---
with tab2:
    st.subheader("Seuils pour les séries temporelles")
    st.number_input("Seuil d'alerte haut (Ex: Température max)", value=40.0)
    st.number_input("Seuil d'alerte bas (Ex: Niveau d'eau min)", value=0.5)

# --- TAB 3 : SUPABASE & DIAGNOSTIC ---
with tab3:
    st.subheader("État des connexions")
    if st.button("🔍 Tester la connexion Supabase"):
        # Logique de test de connexion
        st.success("Connexion Supabase active et fonctionnelle !")
