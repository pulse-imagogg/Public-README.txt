# app.py
import streamlit as st
import pandas as pd
from scraper import collect_all
from analyzer import analyze_post
from datetime import datetime
import json

st.set_page_config(page_title="🎧 Pulse IMAGOGG", page_icon="🌍")

st.title("🎧 Pulse IMAGOGG")
st.markdown("*Prototipo de monitoreo de opinión para impacto social*")

# Sidebar: Configuración
with st.sidebar:
    st.header("⚙️ Configuración")
    keywords_input = st.text_area(
        "Keywords para monitorear (una por línea)",
        value="scaling impact\ngrassroots innovation\nlocal solutions\npoverty alleviation",
        height=100
    )
    keywords = [k.strip() for k in keywords_input.split('\n') if k.strip()]
    
    run_btn = st.button("🔍 Buscar menciones", type="primary")
    
    st.markdown("---")
    st.info("💡 **Puente Claude**: Analiza resultados con tu propia instancia de Claude")

# Estado para almacenar resultados
if 'results' not in st.session_state:
    st.session_state.results = []

if run_btn and keywords:
    with st.spinner("Escaneando fuentes públicas..."):
        posts = collect_all(keywords)
        analyzed = []
        for post in posts:
            analysis = analyze_post(post['content'])
            analyzed.append({**post, **analysis, "analyzed_at": datetime.now().isoformat()})
        
        st.session_state.results = analyzed
        st.success(f"✅ Analizadas {len(analyzed)} menciones")

# Mostrar resultados
if st.session_state.results:
    df = pd.DataFrame(st.session_state.results)
    
    # Filtros
    col1, col2 = st.columns(2)
    with col1:
        sentiment_filter = st.multiselect(
            "Filtrar por sentimiento",
            options=["positive", "neutral", "negative"],
            default=["positive", "neutral", "negative"]
        )
    with col2:
        source_filter = st.multiselect(
            "Filtrar por fuente",
            options=df["source"].unique(),
            default=df["source"].unique()
        )
    
    df_filtered = df[
        df["sentiment"].isin(sentiment_filter) & 
        df["source"].isin(source_filter)
    ]
    
    # Métricas rápidas
    st.subheader("📊 Resumen")
    col1, col2, col3 = st.columns(3)
    col1.metric("Menciones", len(df_filtered))
    col2.metric("Sentimiento positivo", f"{len(df_filtered[df_filtered['sentiment']=='positive'])}")
    col3.metric("Alta relevancia", f"{len(df_filtered[df_filtered['relevance_to_grassroots']>=7])}")
    
    # Tabla interactiva
    st.subheader("📋 Menciones analizadas")
    st.dataframe(
        df_filtered[["published", "source", "title", "sentiment", "relevance_to_grassroots", "actionable_insight"]],
        use_container_width=True
    )
    
    # 🔗 PUENTE CLAUDE: Botón para exportar
    st.markdown("---")
    st.subheader("🤖 Analizar con tu Claude")
    
    if st.button("📋 Generar prompt para Claude"):
        # Seleccionar top 3 menciones más relevantes
        top_mentions = df_filtered.nlargest(3, 'relevance_to_grassroots')[['title', 'content', 'sentiment', 'actionable_insight']]
        
        prompt = f"""Eres un estratega de impacto social para IMAGOGG. 
Analiza estas menciones recientes sobre temas de desarrollo local y proporciona:
1. Tendencias clave que observes
2. Oportunidades de escalar lo que funciona
3. Riesgos o brechas a considerar

Menciones analizadas (formato: título | contenido | sentimiento | insight):
{top_mentions.to_string()}

Contexto adicional: Keywords monitoreadas: {', '.join(keywords)}
Fecha de recolección: {datetime.now().strftime('%Y-%m-%d')}

Devuelve tu análisis en español, conciso y accionable."""
        
        st.code(prompt, language="text")
        st.info("👆 Copia este texto y pégalo en tu interfaz de Claude para un análisis profundo.")
    
    # Exportar a CSV
    csv = df_filtered.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        "💾 Descargar resultados (CSV)",
        data=csv,
        file_name=f"pulse_imagog_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

else:
    st.info("👈 Configura tus keywords y haz clic en 'Buscar menciones' para comenzar")

# Footer
st.markdown("---")
st.caption("🎁 Prototipo desarrollado con recursos 100% gratuitos. ¿Listo para escalar? [Contactar desarrollador]")