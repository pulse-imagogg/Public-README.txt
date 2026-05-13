import streamlit as st
import pandas as pd
import plotly.express as px
import feedparser
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
import requests
from datetime import datetime, timedelta
import re
import hashlib

st.set_page_config(page_title="🎧 Pulse IMAGOGG", page_icon="🌍", layout="wide")

st.title("🎧 Pulse IMAGOGG")
st.markdown("*Monitor de opinión pública para impacto social | Búsqueda profunda + análisis IA*")

# --- ESTADO ---
if 'results' not in st.session_state:
    st.session_state.results = []
if 'linkedin_urls' not in st.session_state:
    st.session_state.linkedin_urls = []

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuración")
    
    keywords = st.text_area(
        "Keywords (una por línea)",
        value="scaling impact\ngrassroots innovation\nlocal solutions\npoverty alleviation",
        height=100
    )
    keywords_list = [k.strip() for k in keywords.split('\n') if k.strip()]
    
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
    
    # LinkedIn manual
    st.subheader("🔗 LinkedIn (URLs públicas)")
    linkedin_input = st.text_area(
        "Pega URLs públicas de posts o perfiles (una por línea)",
        placeholder="https://www.linkedin.com/posts/...\nhttps://www.linkedin.com/in/..."
    )
    linkedin_urls = [u.strip() for u in linkedin_input.split('\n') if u.strip() and 'linkedin.com' in u]
    
    st.divider()
    run_btn = st.button("🔍 Ejecutar búsqueda profunda", type="primary", use_container_width=True)

# --- RECOLECCIÓN ---
def fetch_deep_search(keywords, start_d, end_d):
    posts = []
    ddgs = DDGS()
    
    for kw in keywords:
        try:
            # Búsqueda web general filtrada por fecha
            results = ddgs.text(kw, max_results=15, timelimit=f"{start_d.strftime('%Y-%m-%d')}..{end_d.strftime('%Y-%m-%d')}")
            for r in results:
                posts.append({
                    "source": "DuckDuckGo Web",
                    "title": r["title"],
                    "content": r.get("body", r["title"]),
                    "link": r["href"],
                    "published": datetime.now().date(),
                    "keyword": kw
                })
            
            # Búsqueda específica en LinkedIn (public posts)
            li_results = ddgs.text(f"site:linkedin.com/posts/ {kw}", max_results=5, timelimit=f"{start_d.strftime('%Y-%m-%d')}..{end_d.strftime('%Y-%m-%d')}")
            for r in li_results:
                posts.append({
                    "source": "LinkedIn (Búsqueda pública)",
                    "title": r["title"],
                    "content": r.get("body", r["title"]),
                    "link": r["href"],
                    "published": datetime.now().date(),
                    "keyword": kw
                })
        except Exception as e:
            st.warning(f"⚠️ Error en búsqueda para '{kw}': {e}")
            
    # RSS tradicionales (Google News, Reddit)
    for kw in keywords:
        feeds = [
            f"https://news.google.com/rss/search?q={kw.replace(' ', '+')}&hl=es&gl=CL&ceid=CL:es",
            f"https://www.reddit.com/search.rss?q={kw.replace(' ', '+')}&sort=new"
        ]
        for url in feeds:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:3]:
                    posts.append({
                        "source": "Google News" if "google" in url else "Reddit",
                        "title": entry.title,
                        "content": re.sub(r'<.*?>', '', entry.get("summary", "")),
                        "link": entry.link,
                        "published": datetime.now().date(),
                        "keyword": kw
                    })
            except:
                pass
                
    # Deduplicar por link
    seen = set()
    unique_posts = []
    for p in posts:
        link_hash = hashlib.md5(p["link"].encode()).hexdigest()
        if link_hash not in seen:
            seen.add(link_hash)
            unique_posts.append(p)
            
    return unique_posts

def fetch_linkedin_manual(urls):
    posts = []
    for url in urls:
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            res = requests.get(url, headers=headers, timeout=5)
            soup = BeautifulSoup(res.text, "html.parser")
            title = soup.find("title").get_text() if soup.find("title") else "LinkedIn Post"
            meta_desc = soup.find("meta", {"name": "description"})
            content = meta_desc["content"] if meta_desc else "Contenido no accesible públicamente"
            posts.append({
                "source": "LinkedIn (URL manual)",
                "title": title,
                "content": content[:500],
                "link": url,
                "published": datetime.now().date(),
                "keyword": "manual"
            })
        except:
            posts.append({
                "source": "LinkedIn (URL manual)",
                "title": "Error de acceso",
                "content": "LinkedIn bloquea scraping automático. Usa este método solo para URLs públicas.",
                "link": url,
                "published": datetime.now().date(),
                "keyword": "manual"
            })
    return posts

# --- ANÁLISIS ---
def analyze_post(content):
    # Heurística rápida + gratuita (sin API externa)
    text = content.lower()
    pos = ["éxito", "impacto", "comunidad", "avanza", "logro", "success", "impact", "progress"]
    neg = ["crisis", "fracaso", "problema", "denuncia", "fail", "crisis", "denounce"]
    grassroots = ["local", "base", "territorio", "comunidad", "grassroots", "barrio", "rural"]
    
    p_score = sum(1 for w in pos if w in text)
    n_score = sum(1 for w in neg if w in text)
    
    sentiment = "positive" if p_score > n_score else ("negative" if n_score > p_score else "neutral")
    relevance = min(10, sum(2 for w in grassroots if w in text) + 3)
    
    insight = None
    if "necesita" in text or "need" in text or "buscamos" in text:
        insight = "Oportunidad de colaboración o apoyo"
    elif "éxito" in text or "success" in text or "resultados" in text:
        insight = "Caso de éxito para escalar"
        
    return {"sentiment": sentiment, "relevance_to_grassroots": relevance, "actionable_insight": insight}

# --- EJECUCIÓN ---
if run_btn and keywords_list:
    with st.spinner("🔍 Ejecutando búsqueda profunda en múltiples fuentes..."):
        auto_posts = fetch_deep_search(keywords_list, start_date, end_date)
        li_posts = fetch_linkedin_manual(linkedin_urls)
        all_posts = auto_posts + li_posts
        
        if not all_posts:
            st.warning("No se encontraron menciones. Intenta ampliar el rango de fechas o ajustar keywords.")
        else:
            results = []
            for p in all_posts:
                analysis = analyze_post(p["content"])
                results.append({**p, **analysis, "analyzed_at": datetime.now().isoformat()})
            
            st.session_state.results = results
            st.success(f"✅ {len(results)} menciones recolectadas y analizadas")

# --- UI PRINCIPAL ---
if st.session_state.results:
    df = pd.DataFrame(st.session_state.results)
    df["published_date"] = pd.to_datetime(df["published"]).dt.date
    
    # Filtros de fuente
    sources = sorted(df["source"].unique())
    selected_sources = st.multiselect("🌐 Filtrar por fuente", options=sources, default=sources)
    df_filtered = df[df["source"].isin(selected_sources)]
    
    # 🔹 MÉTRICAS Y GRÁFICOS (COLAPSABLES)
    with st.expander("📊 Ver Dashboard de Métricas y Gráficos", expanded=False):
        if not df_filtered.empty:
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Total Menciones", len(df_filtered))
            k2.metric("Positivas", f"{len(df_filtered[df_filtered['sentiment']=='positive'])}")
            k3.metric("Relevancia Alta (≥7)", f"{len(df_filtered[df_filtered['relevance_to_grassroots']>=7])}")
            k4.metric("Insights", f"{df_filtered['actionable_insight'].notna().sum()}")
            
            st.divider()
            c1, c2 = st.columns(2)
            # Sentimiento
            fig1 = px.pie(df_filtered["sentiment"].value_counts().reset_index(), names="sentiment", values="count", 
                          title="Distribución por Sentimiento", color_discrete_map={"positive":"#28a745","neutral":"#ffc107","negative":"#dc3545"})
            c1.plotly_chart(fig1, use_container_width=True)
            # Fuente
            fig2 = px.bar(df_filtered["source"].value_counts().reset_index(), x="source", y="count", title="Menciones por Fuente")
            fig2.update_layout(xaxis_tickangle=-45)
            c2.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Sin datos para mostrar con los filtros actuales.")

    st.divider()
    
    # 🔹 TABLA
    st.subheader("📋 Menciones Analizadas")
    st.dataframe(df_filtered[["published_date", "source", "title", "sentiment", "relevance_to_grassroots", "actionable_insight", "link"]], 
                 use_container_width=True, height=350)
    
    st.divider()
    
    # 🔗 PUENTE CLAUDE & EXPORT
    st.subheader("🤖 Analizar con tu Claude")
    if st.button("📋 Generar prompt estratégico para Claude", type="secondary"):
        top = df_filtered.nlargest(3, 'relevance_to_grassroots')[['title', 'content', 'sentiment', 'actionable_insight']]
        prompt = f"""Eres estratega de impacto social para IMAGOGG.
Analiza estas menciones recientes sobre {', '.join(keywords_list)}:
{top.to_string(index=False)}

Entrega:
1. Tendencias emergentes
2. Oportunidades de escalar lo que funciona
3. Brechas o riesgos a monitorear

Responde en español, conciso y accionable. Fecha: {datetime.now().strftime('%Y-%m-%d')}"""
        st.code(prompt, language="text")
        st.info("👆 Copia y pega en tu interfaz de Claude.")
        
    csv = df_filtered.to_csv(index=False, encoding='utf-8-sig')
    st.download_button("💾 Descargar CSV", data=csv, file_name=f"pulse_imagogg_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv")

else:
    st.info("👈 Configura keywords, rango y/o URLs de LinkedIn. Luego ejecuta la búsqueda.")

st.markdown("---")
st.caption("🎁 Prototipo 100% gratuito | Búsqueda profunda + análisis local | ¿Listo para escalar? [Contactar chileautomatico.cl]")
