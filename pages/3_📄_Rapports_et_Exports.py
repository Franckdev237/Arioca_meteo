import streamlit as st
import pandas as pd
import io
from datetime import datetime

# Imports pour le PDF avec ReportLab
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

st.title("📄 Générateur de Rapports & Exports")
st.caption("Créez des syntheses PDF automatisées et exportez vos données nettoyées.")

# Fonction pour créer un PDF
def generer_pdf(titre_rapport, auteur, remarques, df_apercu):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()

    # Titre du rapport
    title_style = ParagraphStyle('TitreRapport', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor("#1E3A8A"), spaceAfter=12)
    story.append(Paragraph(f"<b>{titre_rapport}</b>", title_style))
    story.append(Spacer(1, 10))

    # Métadonnées
    meta_text = f"<b>Date de génération :</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}<br/><b>Auteur :</b> {auteur}"
    story.append(Paragraph(meta_text, styles['Normal']))
    story.append(Spacer(1, 15))

    # Remarques / Observations
    if remarques:
        story.append(Paragraph("<b>Observations & Notes :</b>", styles['Heading2']))
        story.append(Paragraph(remarques, styles['Normal']))
        story.append(Spacer(1, 15))

    # Tableau des données (Aperçu des 10 premières lignes)
    if df_apercu is not None and not df_apercu.empty:
        story.append(Paragraph("<b>Aperçu des données (10 premières lignes) :</b>", styles['Heading2']))
        
        # Préparation des données pour le tableau ReportLab
        data = [list(df_apercu.columns)] + df_apercu.head(10).astype(str).values.tolist()
        t = Table(data)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2563EB")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#F3F4F6")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(t)

    doc.build(story)
    buffer.seek(0)
    return buffer

# Interface d'import pour rapport
uploaded_file = st.file_uploader("Chargez un fichier pour générer un rapport PDF", type=["csv", "xlsx"])

if uploaded_file:
    df = pd.read_csv(uploaded_file, sep=None, engine='python') if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    st.dataframe(df.head(5), use_container_width=True)

    st.subheader("📝 Informations du Rapport")
    col1, col2 = st.columns(2)
    with col1:
        titre = st.text_input("Titre du Rapport", value="Rapport d'Analyse de Données")
    with col2:
        auteur = st.text_input("Nom de l'Analyste / Auteur", value="Equipe Data")
        
    remarques = st.text_area("Remarques / Conclusions", value="Les données ont été vérifiées et validées.")

    st.markdown("---")
    
    col_pdf, col_excel = st.columns(2)

    with col_pdf:
        if st.button("🔴 Générer le PDF"):
            pdf_data = generer_pdf(titre, auteur, remarques, df)
            st.download_button(
                label="📥 Télécharger le Rapport PDF",
                data=pdf_data,
                file_name=f"rapport_{datetime.now().strftime('%Y%m%m_%H%M%S')}.pdf",
                mime="application/pdf"
            )

    with col_excel:
        # Export Excel via BytesIO
        output_excel = io.BytesIO()
        with pd.ExcelWriter(output_excel, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Donnees_Propres', index=False)
        output_excel.seek(0)

        st.download_button(
            label="🟢 Télécharger en Excel (.xlsx)",
            data=output_excel,
            file_name=f"export_donnees_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
