import streamlit as st
import pandas as pd
import plotly.express as px
import feedparser
from duckduckgo_search import DDGS
from datetime import datetime, timedelta
import re
import hashlib

st.set_page_config(page_title="🎧 Pulse IMAGOGG", page_icon="🌍", layout="wide")

st.title("🎧 Pulse IMAGOGG")
st.markdown("*Monitor de opinión pública | Búsqueda automática en LinkedIn + otras fuentes*")

# --- ESTADO ---
if 'results' not in st.session_state:
    st.session_state.results = []

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuración")
    
    keywords = st.text_area(
        " Keywords a monitorear (una por línea)",
        value="scaling impact\ngrassroots innovation\nlocal solutions\npoverty alleviation",
        height=100
    )
    keywords_list = [k.strip() for k in keywords.split('\n') if k.strip()]
    
    st.divider()
    
    # Fuentes a buscar
    st.subheader("🌐 Fuentes de búsqueda")
    search_linkedin = st.checkbox("✅ LinkedIn (posts, artículos, perfiles)", value=True)
    search_twitter = st.checkbox("Twitter/X", value=True)
    search_news = st.checkbox("Noticias y blogs", value=True)
    search_reddit = st.checkbox("Reddit y foros", value=True)
    
    st.divider()
    
    # Rango de fechas
    today = datetime.now().date()
    date_range = st.date_input(
        "📅 Rango de fechas",
        value=(today - timedelta(days=30), today),
        max_value=today
    )
    start_date, end_date = date_range
    
    st.divider()
    run_btn = st.button("🔍 Buscar menciones automáticamente", type="primary", use_container_width=True)

# --- RECOLECCIÓN ---
def search_linkedin_automatico(keywords, start_d, end_d):
    """Busca AUTOMÁTICAMENTE en LinkedIn usando DuckDuckGo"""
    posts = []
    ddgs = DDGS()
    
    for kw in keywords:
        try:
            # 1. Posts públicos de LinkedIn
            li_posts = ddgs.text(
                f"site:linkedin.com/posts/ {kw}",
                max_results=10,
                timelimit=f"{start_d.strftime('%Y-%m-%d')}..{end_d.strftime('%Y-%m-%d')}"
            )
            for r in li_posts:
                posts.append({
                    "source": "LinkedIn Posts",
                    "title": r["title"][:100],
                    "content": r.get("body", r["title"])[:300],
                    "link": r["href"],
                    "published": datetime.now().date(),
                    "keyword": kw,
                    "platform": "LinkedIn"
                })
            
            # 2. Artículos de LinkedIn (LinkedIn Pulse)
            li_articles = ddgs.text(
                f"site:linkedin.com/pulse/ {kw}",
                max_results=5,
                timelimit=f"{start_d.strftime('%Y-%m-%d')}..{end_d.strftime('%Y-%m-%d')}"
            )
            for r in li_articles:
                posts.append({
                    "source": "LinkedIn Artículos",
                    "title": r["title"][:100],
                    "content": r.get("body", r["title"])[:300],
                    "link": r["href"],
                    "published": datetime.now().date(),
                    "keyword": kw,
                    "platform": "LinkedIn"
                })
                
            # 3. Perfiles que mencionan el tema
            li_profiles = ddgs.text(
                f"site:linkedin.com/in/ {kw}",
                max_results=5,
                timelimit=f"{start_d.strftime('%Y-%m-%d')}..{end_d.strftime('%Y-%m-%d')}"
            )
            for r in li_profiles:
                posts.append({
                    "source": "LinkedIn Perfiles",
                    "title": r["title"][:100],
                    "content": r.get("body", "Perfil profesional")[:300],
                    "link": r["href"],
                    "published": datetime.now().date(),
                    "keyword": kw,
                    "platform": "LinkedIn"
                })
                
        except Exception as e:
            st.warning(f"⚠️ Error buscando LinkedIn para '{kw}': {str(e)[:100]}")
            
    return posts

def search_twitter(keywords, start_d, end_d):
    """Busca en Twitter vía Nitter (sin API)"""
    posts = []
    for kw in keywords:
        try:
            ddgs = DDGS()
            results = ddgs.text(
                f"site:twitter.com {kw} OR site:x.com {kw}",
                max_results=10,
                timelimit=f"{start_d.strftime('%Y-%m-%d')}..{end_d.strftime('%Y-%m-%d')}"
            )
            for r in results:
                posts.append({
                    "source": "Twitter/X",
                    "title": r["title"][:100],
                    "content": r.get("body", r["title"])[:280],
                    "link": r["href"],
                    "published": datetime.now().date(),
                    "keyword": kw,
                    "platform": "Twitter"
                })
        except:
            pass
    return posts

def search_news(keywords, start_d, end_d):
    """Google News vía RSS"""
    posts = []
    for kw in keywords:
        try:
            url = f"https://news.google.com/rss/search?q={kw.replace(' ', '+')}&hl=es&gl=CL&ceid=CL:es"
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:
                posts.append({
                    "source": "Google News",
                    "title": entry.title,
                    "content": re.sub(r'<.*?>', '', entry.get("summary", ""))[:300],
                    "link": entry.link,
                    "published": datetime.now().date(),
                    "keyword": kw,
                    "platform": "News"
                })
        except:
            pass
    return posts

def search_reddit(keywords, start_d, end_d):
    """Reddit vía RSS"""
    posts = []
    for kw in keywords:
        try:
            url = f"https://www.reddit.com/search.rss?q={kw.replace(' ', '+')}&sort=new"
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:
                posts.append({
                    "source": "Reddit",
                    "title": entry.title,
                    "content": re.sub(r'<.*?>', '', entry.get("summary", ""))[:300],
                    "link": entry.link,
                    "published": datetime.now().date(),
                    "keyword": kw,
                    "platform": "Reddit"
                })
        except:
            pass
    return posts

# --- ANÁLISIS ---
def analyze_post(content):
    """Análisis local sin API"""
    text = content.lower()
    pos_words = ["éxito", "impacto", "comunidad", "avanza", "logro", "success", "impact", "progress", "innovación", "innovation"]
    neg_words = ["crisis", "fracaso", "problema", "denuncia", "fail", "crisis", "denounce", "conflicto"]
    grassroots_words = ["local", "base", "territorio", "comunidad", "grassroots", "barrio", "rural", "organizaciones de base"]
    
    p_score = sum(1 for w in pos_words if w in text)
    n_score = sum(1 for w in neg_words if w in text)
    
    sentiment = "positive" if p_score > n_score else ("negative" if n_score > p_score else "neutral")
    relevance = min(10, sum(2 for w in grassroots_words if w in text) + 3)
    
    insight = None
    if any(w in text for w in ["necesita", "need", "buscamos", "buscando", "requiere"]):
        insight = "🤝 Oportunidad de colaboración"
    elif any(w in text for w in ["éxito", "success", "resultados", "logros", "achievements"]):
        insight = "📈 Caso de éxito para escalar"
    elif any(w in text for w in ["desafío", "challenge", "obstáculo", "barrier"]):
        insight = "⚠️ Desafío a monitorear"
        
    return {"sentiment": sentiment, "relevance_to_grassroots": relevance, "actionable_insight": insight}

# --- EJECUCIÓN ---
if run_btn and keywords_list:
    with st.spinner("🔍 Buscando automáticamente en múltiples fuentes..."):
        all_posts = []
        
        # Búsquedas según checkboxes
        if search_linkedin:
            with st.status("🔎 Buscando en LinkedIn...", expanded=False) as status:
                li_posts = search_linkedin_automatico(keywords_list, start_date, end_date)
                all_posts.extend(li_posts)
                status.update(label=f"✅ LinkedIn: {len(li_posts)} resultados encontrados")
        
        if search_twitter:
            tw_posts = search_twitter(keywords_list, start_date, end_date)
            all_posts.extend(tw_posts)
            
        if search_news:
            news_posts = search_news(keywords_list, start_date, end_date)
            all_posts.extend(news_posts)
            
        if search_reddit:
            reddit_posts = search_reddit(keywords_list, start_date, end_date)
            all_posts.extend(reddit_posts)
        
        if not all_posts:
            st.warning(" No se encontraron menciones. Intenta:\n- Ampliar el rango de fechas\n- Usar keywords más generales\n- Verificar que las fuentes estén seleccionadas")
        else:
            # Deduplicar
            seen = set()
            unique_posts = []
            for p in all_posts:
                link_hash = hashlib.md5(p["link"].encode()).hexdigest()
                if link_hash not in seen:
                    seen.add(link_hash)
                    unique_posts.append(p)
            
            # Analizar
            results = []
            for p in unique_posts:
                analysis = analyze_post(p["content"])
                results.append({**p, **analysis, "analyzed_at": datetime.now().isoformat()})
            
            st.session_state.results = results
            st.success(f"✅ {len(results)} menciones encontradas y analizadas")

# --- UI PRINCIPAL ---
if st.session_state.results:
    df = pd.DataFrame(st.session_state.results)
    
    # Filtros
    col1, col2 = st.columns(2)
    with col1:
        sources = sorted(df["source"].unique())
        selected_sources = st.multiselect("🌐 Filtrar por fuente", options=sources, default=sources)
    with col2:
        platforms = sorted(df["platform"].unique())
        selected_platforms = st.multiselect("📱 Filtrar por plataforma", options=platforms, default=platforms)
    
    df_filtered = df[df["source"].isin(selected_sources) & df["platform"].isin(selected_platforms)]
    
    # 🔹 DASHBOARD COLAPSABLE
    with st.expander("📊 Ver Dashboard de Métricas", expanded=False):
        if not df_filtered.empty:
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Total Menciones", len(df_filtered))
            k2.metric("Positivas", f"{len(df_filtered[df_filtered['sentiment']=='positive'])}")
            k3.metric("Relevancia Alta (≥7)", f"{len(df_filtered[df_filtered['relevance_to_grassroots']>=7])}")
            k4.metric("Insights Accionables", f"{df_filtered['actionable_insight'].notna().sum()}")
            
            st.divider()
            c1, c2 = st.columns(2)
            
            # Gráfico 1: Por plataforma
            fig_plat = px.pie(df_filtered["platform"].value_counts().reset_index(), 
                             names="platform", values="count", 
                             title="Distribución por Plataforma",
                             color_discrete_map={"LinkedIn":"#0A66C2","Twitter":"#1DA1F2","News":"#4285F4","Reddit":"#FF4500"})
            c1.plotly_chart(fig_plat, use_container_width=True)
            
            # Gráfico 2: Por sentimiento
            fig_sent = px.bar(df_filtered["sentiment"].value_counts().reset_index(),
                             x="sentiment", y="count",
                             title="Distribución por Sentimiento",
                             color="sentiment",
                             color_discrete_map={"positive":"#28a745","neutral":"#ffc107","negative":"#dc3545"})
            c2.plotly_chart(fig_sent, use_container_width=True)
            
            # Gráfico 3: LinkedIn vs Otros
            if "LinkedIn" in df_filtered["platform"].values:
                li_count = len(df_filtered[df_filtered["platform"]=="LinkedIn"])
                other_count = len(df_filtered) - li_count
                fig_li = px.bar(
                    pd.DataFrame({"Tipo": ["LinkedIn", "Otras fuentes"], "Menciones": [li_count, other_count]}),
                    x="Tipo", y="Menciones",
                    title="LinkedIn vs Otras Fuentes",
                    color="Tipo"
                )
                st.plotly_chart(fig_li, use_container_width=True)
        else:
            st.info("Sin datos con los filtros actuales")

    st.divider()
    
    # 🔹 TABLA
    st.subheader(f"📋 {len(df_filtered)} menciones encontradas")
    st.dataframe(
        df_filtered[["platform", "source", "published", "title", "sentiment", "relevance_to_grassroots", "actionable_insight", "link"]],
        use_container_width=True,
        height=400
    )
    
    st.divider()
    
    # 🔗 PUENTE CLAUDE
    st.subheader("🤖 Análisis estratégico con Claude")
    if st.button("📋 Generar prompt para Claude", type="secondary"):
        top_mentions = df_filtered.nlargest(5, 'relevance_to_grassroots')[['platform', 'title', 'sentiment', 'actionable_insight']]
        prompt = f"""Eres estratega senior de impacto social para IMAGOGG.

CONTEXTO: Búsqueda automática sobre: {', '.join(keywords_list)}
FECHA: {datetime.now().strftime('%Y-%m-%d')}
FUENTES: {', '.join(selected_platforms)}

TOP 5 MENCIONES MÁS RELEVANTES:
{top_mentions.to_string(index=False)}

TAREA:
1. Identifica 2-3 tendencias emergentes
2. Señala oportunidades concretas de escalar lo que funciona
3. Detecta brechas o riesgos que IMAGOGG debería monitorear
4. Recomienda 1 acción prioritaria para las próximas 2 semanas

Responde en español, ejecutivo y accionable (máx 400 palabras)."""
        
        st.code(prompt, language="text")
        st.info("👆 Copia este prompt y pégalo en tu interfaz de Claude para obtener análisis estratégico profundo.")
    
    # Exportar
    csv = df_filtered.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        "💾 Descargar resultados completos (CSV)",
        data=csv,
        file_name=f"pulse_imagogg_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv"
    )

else:
    # Estado inicial
    st.info("👈 Configura tus keywords, selecciona las fuentes y haz clic en 'Buscar menciones automáticamente'")
    
    st.markdown("""
    ### 💡 ¿Cómo funciona?
    - **LinkedIn**: Busca automáticamente posts, artículos y perfiles públicos que mencionen tus keywords
    - **Twitter/X**: Encuentra tweets públicos sobre los temas
    - **Noticias**: Rastrea Google News y blogs relevantes
    - **Reddit**: Monitorea discusiones en foros y comunidades
    
    Todo 100% automático. Sin necesidad de URLs previas.
    """)

st.markdown("---")
st.caption("🎁 Prototipo 100% gratuito | Búsqueda automática multi-plataforma | Desarrollado para IMAGOGG")
