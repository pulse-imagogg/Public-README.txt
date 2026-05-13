import streamlit as st
import pandas as pd
import plotly.express as px
from scraper import collect_all
from analyzer import analyze_post
from datetime import datetime, timedelta
import time

# Configuración de página
st.set_page_config(
    page_title="🎧 Pulse IMAGOGG",
    page_icon="🌍",
    layout="wide"
)

st.title("🎧 Pulse IMAGOGG")
st.markdown("*Monitor de opinión pública para impacto social*")

# --- INICIALIZACIÓN DE ESTADO ---
if 'results' not in st.session_state:
    st.session_state.results = []
if 'last_fetch' not in st.session_state:
    st.session_state.last_fetch = None

# --- SIDEBAR: CONFIGURACIÓN ---
with st.sidebar:
    st.header("⚙️ Configuración de Búsqueda")
    
    keywords = st.text_area(
        "Keywords (una por línea)",
        value="scaling impact\ngrassroots innovation\nlocal solutions",
        height=100
    ).strip()
    keywords_list = [k.strip() for k in keywords.split('\n') if k.strip()]
    
    st.divider()
    
    # Filtro de fechas
    st.subheader("📅 Rango de Fechas")
    today = datetime.now().date()
    date_range = st.date_input(
        "Selecciona rango",
        value=(today - timedelta(days=30), today),
        max_value=today
    )
    
    # Filtro de fuentes (se activa después de buscar)
    if st.session_state.results:
        st.subheader("🌐 Filtrar por Fuentes")
        available_sources = sorted(set(r["source"] for r in st.session_state.results))
        selected_sources = st.multiselect(
            "Selecciona fuentes",
            options=available_sources,
            default=available_sources
        )
    else:
        st.info("Las fuentes aparecerán después de buscar")
        
    st.divider()
    run_btn = st.button("🔍 Buscar menciones", type="primary", use_container_width=True)

# --- LÓGICA PRINCIPAL ---
if run_btn and keywords_list:
    with st.spinner("Escaneando fuentes públicas..."):
        # 1. Recolección
        posts = collect_all(keywords_list)
        if not posts:
            st.warning("No se encontraron menciones con estas keywords en las últimas 48h.")
        else:
            # 2. Análisis
            analyzed = []
            for post in posts:
                analysis = analyze_post(post['content'])
                # Parsear fecha RSS de forma segura
                raw_date = post.get('published', '')
                try:
                    # feedparser a veces devuelve string o struct_time
                    if isinstance(raw_date, str):
                        pub_date = pd.to_datetime(raw_date, dayfirst=True)
                    else:
                        pub_date = pd.to_datetime(raw_date)
                except:
                    pub_date = datetime.now()
                
                analyzed.append({
                    **post,
                    **analysis,
                    "published_date": pub_date.date(),
                    "published_time": pub_date
                })
            
            st.session_state.results = analyzed
            st.session_state.last_fetch = datetime.now()
            st.success(f"✅ {len(analyzed)} menciones analizadas")

# --- DASHBOARD & VISUALIZACIÓN ---
if st.session_state.results:
    df = pd.DataFrame(st.session_state.results)
    
    # Aplicar filtros
    start_date, end_date = date_range
    filtered_df = df[df["published_date"].between(start_date, end_date)]
    
    if 'selected_sources' in locals() and selected_sources:
        filtered_df = filtered_df[filtered_df["source"].isin(selected_sources)]
        
    if filtered_df.empty:
        st.info("No hay resultados que coincidan con los filtros seleccionados.")
    else:
        # 🔹 KPIs
        st.subheader("📊 Métricas Clave")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Menciones", len(filtered_df))
        k2.metric("Sentimiento Positivo", f"{len(filtered_df[filtered_df['sentiment']=='positive'])}")
        k3.metric("Relevancia Alta (≥7)", f"{len(filtered_df[filtered_df['relevance_to_grassroots']>=7])}")
        k4.metric("Insights Accionables", f"{filtered_df['actionable_insight'].notna().sum()}")
        
        st.divider()
        
        # 🔹 Gráficos
        col1, col2 = st.columns(2)
        
        # Gráfico 1: Distribución por sentimiento
        sentiment_counts = filtered_df["sentiment"].value_counts().reset_index()
        sentiment_counts.columns = ["Sentimiento", "Cantidad"]
        fig_sent = px.bar(sentiment_counts, x="Sentimiento", y="Cantidad", 
                          color="Sentimiento", color_discrete_map={
                              "positive": "#28a745", "neutral": "#ffc107", "negative": "#dc3545"
                          })
        fig_sent.update_layout(title="Distribución por Sentimiento", showlegend=False)
        col1.plotly_chart(fig_sent, use_container_width=True)
        
        # Gráfico 2: Menciones por fuente
        source_counts = filtered_df["source"].value_counts().reset_index()
        source_counts.columns = ["Fuente", "Menciones"]
        fig_src = px.pie(source_counts, names="Fuente", values="Menciones", 
                         title="Distribución por Fuente", hole=0.4)
        col2.plotly_chart(fig_src, use_container_width=True)
        
        # Gráfico 3: Tendencia temporal
        trend = filtered_df.groupby("published_date").size().reset_index()
        trend.columns = ["Fecha", "Menciones"]
        fig_trend = px.line(trend, x="Fecha", y="Menciones", markers=True, 
                            title="Menciones en el Tiempo")
        st.plotly_chart(fig_trend, use_container_width=True)
        
        st.divider()
        
        # 🔹 Tabla detallada
        st.subheader("📋 Menciones Analizadas")
        st.dataframe(
            filtered_df[["published_time", "source", "title", "sentiment", "relevance_to_grassroots", "actionable_insight"]],
            use_container_width=True,
            height=400
        )
        
        st.divider()
        
        # 🔗 PUENTE CLAUDE & EXPORT
        st.subheader("🤖 Analizar con tu Claude")
        if st.button("📋 Generar prompt para Claude", type="secondary"):
            top_mentions = filtered_df.nlargest(3, 'relevance_to_grassroots')[['title', 'content', 'sentiment', 'actionable_insight']]
            prompt = f"""Eres un estratega de impacto social para IMAGOGG. 
Analiza estas menciones recientes y proporciona:
1. Tendencias clave que observes
2. Oportunidades de escalar lo que funciona
3. Riesgos o brechas a considerar

Menciones (título | contenido | sentimiento | insight):
{top_mentions.to_string()}

Keywords: {', '.join(keywords_list)}
Fecha análisis: {datetime.now().strftime('%Y-%m-%d')}
Devuelve tu análisis en español, conciso y accionable."""
            
            st.code(prompt, language="text")
            st.info("👆 Copia y pega en tu interfaz de Claude para análisis estratégico profundo.")
        
        # Exportar
        csv = filtered_df.to_csv(index=False, encoding='utf-8-sig')
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
st.caption("🎁 Prototipo 100% gratuito | Desarrollado para IMAGOGG | ¿Listo para escalar? [Contactar chileautomatico.cl]")
st.caption("🎁 Prototipo desarrollado con recursos 100% gratuitos. ¿Listo para escalar? [Contactar chileautomatico.cl]")
