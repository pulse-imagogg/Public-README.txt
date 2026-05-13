import streamlit as st
import pandas as pd
import plotly.express as px
import feedparser
from duckduckgo_search import DDGS
from datetime import datetime, timedelta
import re, hashlib, requests

st.set_page_config(page_title="🎧 Pulse IMAGOGG", page_icon="🌍", layout="wide")
st.title("🎧 Pulse IMAGOGG")
st.markdown("*Monitor de opinión pública | Fuentes verificadas + análisis local*")

# --- ESTADO ---
if 'results' not in st.session_state:
    st.session_state.results = []
if 'debug_mode' not in st.session_state:
    st.session_state.debug_mode = False

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuración")
    
    keywords = st.text_area("Keywords (una por línea)", 
                           value="scaling impact\ngrassroots innovation\nlocal solutions", 
                           height=100)
    keywords_list = [k.strip() for k in keywords.split('\n') if k.strip()]
    
    st.divider()
    
    # Fuentes
    st.subheader("🌐 Fuentes")
    sources_config = {
        "Google News": st.checkbox("✅ Google News (RSS)", value=True),
        "Reddit": st.checkbox("✅ Reddit (RSS)", value=True),
        "LinkedIn (limitado)": st.checkbox("⚠️ LinkedIn (búsqueda pública)", value=True),
        "Twitter/X (limitado)": st.checkbox("⚠️ Twitter/X (búsqueda pública)", value=False),
    }
    
    st.divider()
    
    # Tiempo (opciones compatibles con DuckDuckGo)
    st.subheader("📅 Periodo de búsqueda")
    time_options = {
        "Últimas 24 horas": "d",
        "Última semana": "w",
        "Último mes": "m", 
        "Último año": "y",
        "Sin filtro (más resultados)": None
    }
    time_label = st.selectbox("Selecciona", options=list(time_options.keys()), index=2)
    timelimit = time_options[time_label]
    
    st.divider()
    
    # Debug mode
    st.session_state.debug_mode = st.checkbox("🔧 Modo debug (ver queries)", value=False)
    
    st.divider()
    run_btn = st.button("🔍 Buscar", type="primary", use_container_width=True)

# --- RECOLECCIÓN ---
def search_with_fallback(keyword, query_prefix, timelimit, max_results=10):
    """Busca con DuckDuckGo + fallback sin fecha si no hay resultados"""
    ddgs = DDGS()
    results = []
    
    # Intento 1: con filtro de tiempo
    if timelimit:
        try:
            query = f"{query_prefix} {keyword}"
            if st.session_state.debug_mode:
                st.code(f"🔎 Query (con fecha): {query} | timelimit={timelimit}")
            hits = ddgs.text(query, max_results=max_results, timelimit=timelimit)
            results.extend(list(hits))
        except:
            pass
    
    # Fallback: sin filtro de tiempo si no hubo resultados
    if len(results) < 3 and query_prefix.strip():  # Si es búsqueda web
        try:
            query = f"{query_prefix} {keyword}"
            if st.session_state.debug_mode:
                st.code(f"🔎 Fallback (sin fecha): {query}")
            hits = ddgs.text(query, max_results=max_results)
            # Filtrar manualmente por fecha aproximada (título/descripción)
            for h in hits:
                if keyword.lower() in h.get("title","").lower() or keyword.lower() in h.get("body","").lower():
                    results.append(h)
        except:
            pass
            
    return results

def collect_posts(keywords, sources, timelimit):
    posts = []
    
    for kw in keywords:
        # Google News (RSS - siempre funciona)
        if sources.get("Google News"):
            try:
                url = f"https://news.google.com/rss/search?q={kw.replace(' ', '+')}&hl=es&gl=CL&ceid=CL:es"
                feed = feedparser.parse(url)
                for entry in feed.entries[:5]:
                    posts.append({
                        "source": "Google News", "platform": "News",
                        "title": entry.title,
                        "content": re.sub(r'<.*?>', '', entry.get("summary", ""))[:300],
                        "link": entry.link, "published": datetime.now().date(),
                        "keyword": kw
                    })
            except: pass
        
        # Reddit (RSS - funciona bien)
        if sources.get("Reddit"):
            try:
                url = f"https://www.reddit.com/search.rss?q={kw.replace(' ', '+')}&sort=new"
                feed = feedparser.parse(url)
                for entry in feed.entries[:5]:
                    posts.append({
                        "source": "Reddit", "platform": "Forum",
                        "title": entry.title,
                        "content": re.sub(r'<.*?>', '', entry.get("summary", ""))[:300],
                        "link": entry.link, "published": datetime.now().date(),
                        "keyword": kw
                    })
            except: pass
        
        # LinkedIn (búsqueda pública - limitado pero útil)
        if sources.get("LinkedIn (limitado)"):
            li_hits = search_with_fallback(kw, "site:linkedin.com/posts/", timelimit, max_results=8)
            for r in li_hits:
                posts.append({
                    "source": "LinkedIn Posts", "platform": "LinkedIn",
                    "title": r["title"][:120],
                    "content": r.get("body", r["title"])[:300],
                    "link": r["href"], "published": datetime.now().date(),
                    "keyword": kw
                })
            
            # Artículos de LinkedIn Pulse
            li_articles = search_with_fallback(kw, "site:linkedin.com/pulse/", timelimit, max_results=3)
            for r in li_articles:
                posts.append({
                    "source": "LinkedIn Artículos", "platform": "LinkedIn",
                    "title": r["title"][:120],
                    "content": r.get("body", r["title"])[:300],
                    "link": r["href"], "published": datetime.now().date(),
                    "keyword": kw
                })
        
        # Twitter/X (muy limitado, opcional)
        if sources.get("Twitter/X (limitado)"):
            tw_hits = search_with_fallback(kw, "site:twitter.com OR site:x.com", timelimit, max_results=5)
            for r in tw_hits:
                posts.append({
                    "source": "Twitter/X", "platform": "Twitter",
                    "title": r["title"][:120],
                    "content": r.get("body", r["title"])[:280],
                    "link": r["href"], "published": datetime.now().date(),
                    "keyword": kw
                })
    
    # Deduplicar
    seen = set()
    unique = []
    for p in posts:
        h = hashlib.md5(p["link"].encode()).hexdigest()
        if h not in seen:
            seen.add(h)
            unique.append(p)
    
    return unique

# --- ANÁLISIS (igual que antes) ---
def analyze_post(content):
    text = content.lower()
    pos = ["éxito", "impacto", "comunidad", "avanza", "logro", "success", "impact", "progress", "innovación"]
    neg = ["crisis", "fracaso", "problema", "denuncia", "fail", "conflicto"]
    grassroots = ["local", "base", "territorio", "comunidad", "grassroots", "barrio", "rural", "organizaciones"]
    
    p_score = sum(1 for w in pos if w in text)
    n_score = sum(1 for w in neg if w in text)
    sentiment = "positive" if p_score > n_score else ("negative" if n_score > p_score else "neutral")
    relevance = min(10, sum(2 for w in grassroots if w in text) + 3)
    
    insight = None
    if any(w in text for w in ["necesita", "need", "buscamos", "requiere"]):
        insight = "🤝 Oportunidad de colaboración"
    elif any(w in text for w in ["éxito", "success", "resultados", "logros"]):
        insight = "📈 Caso de éxito para escalar"
    return {"sentiment": sentiment, "relevance_to_grassroots": relevance, "actionable_insight": insight}

# --- EJECUCIÓN ---
if run_btn and keywords_list:
    with st.spinner("🔍 Buscando en fuentes públicas..."):
        raw_posts = collect_posts(keywords_list, sources_config, timelimit)
        
        if not raw_posts:
            st.warning("⚠️ No se encontraron resultados. Consejos:\n- Usa keywords más generales\n- Selecciona 'Sin filtro de tiempo'\n- LinkedIn/Twitter tienen acceso limitado sin API")
        else:
            results = [{**p, **analyze_post(p["content"]), "analyzed_at": datetime.now().isoformat()} for p in raw_posts]
            st.session_state.results = results
            st.success(f"✅ {len(results)} menciones encontradas")
            
            # Resumen por fuente
            source_summary = pd.DataFrame(results)["source"].value_counts()
            st.caption(f"Distribución: {', '.join([f'{k}: {v}' for k,v in source_summary.items()])}")

# --- UI ---
if st.session_state.results:
    df = pd.DataFrame(st.session_state.results)
    
    # Filtros
    col1, col2 = st.columns(2)
    with col1:
        src_filter = st.multiselect("Fuente", df["source"].unique(), default=df["source"].unique())
    with col2:
        plat_filter = st.multiselect("Plataforma", df["platform"].unique(), default=df["platform"].unique())
    
    df_f = df[df["source"].isin(src_filter) & df["platform"].isin(plat_filter)]
    
    # Dashboard colapsable
    with st.expander("📊 Métricas", expanded=False):
        if not df_f.empty:
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Total", len(df_f))
            c2.metric("Positivas", len(df_f[df_f["sentiment"]=="positive"]))
            c3.metric("Relevancia ≥7", len(df_f[df_f["relevance_to_grassroots"]>=7]))
            c4.metric("Insights", df_f["actionable_insight"].notna().sum())
            st.divider()
            fig = px.pie(df_f["platform"].value_counts().reset_index(), names="platform", values="count")
            st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    st.dataframe(df_f[["platform","source","published","title","sentiment","relevance_to_grassroots","link"]], use_container_width=True, height=350)
    
    # Puente Claude
    with st.expander("🤖 Análisis con Claude", expanded=False):
        if st.button("📋 Generar prompt"):
            top = df_f.nlargest(3, "relevance_to_grassroots")[["title","sentiment","actionable_insight"]]
            prompt = f"""Eres estratega de IMAGOGG. Analiza estas menciones sobre {', '.join(keywords_list)}:
{top.to_string(index=False)}
Entrega: 1) Tendencias, 2) Oportunidades de escalar, 3) Riesgos. Español, conciso."""
            st.code(prompt)
    
    # Exportar
    st.download_button("💾 CSV", df_f.to_csv(index=False).encode('utf-8-sig'), f"pulse_{datetime.now().strftime('%Y%m%d')}.csv")

else:
    st.info("👈 Configura y haz clic en Buscar")
    with st.expander("ℹ️ Notas técnicas sobre las fuentes"):
        st.markdown("""
        - **Google News/Reddit**: RSS públicos → resultados consistentes ✅
        - **LinkedIn**: Solo posts/artículos públicos indexados por buscadores → resultados limitados ⚠️
        - **Twitter/X**: Acceso restringido desde 2023 → muy limitado sin API paga ⚠️
        - **Para producción**: Se recomienda LinkedIn API + Twitter API v2 + Google Custom Search ($50-200/mes)
        """)

st.markdown("---")
st.caption("🎁 Prototipo gratuito | Fuentes públicas + análisis local | Desarrollado por chileautomatico.cl para IMAGOGG")
