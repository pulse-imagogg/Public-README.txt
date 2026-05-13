# scraper.py
import feedparser, requests, re
from bs4 import BeautifulSoup
from datetime import datetime

def fetch_google_alerts(keywords, lang='es'):
    """Google Alerts via RSS - 100% free"""
    results = []
    for kw in keywords:
        url = f"https://news.google.com/rss/search?q={kw.replace(' ', '+')}&hl={lang}&gl=CL&ceid=CL:{lang}"
        feed = feedparser.parse(url)
        for entry in feed.entries[:3]:  # Limitar para MVP
            results.append({
                "source": "Google News",
                "title": entry.title,
                "content": entry.get("summary", entry.title),
                "link": entry.link,
                "published": entry.get("published", datetime.now().isoformat()),
                "keyword": kw
            })
    return results

def fetch_nitter_twitter(keyword):
    """Twitter vía Nitter (sin API, sin auth)"""
    results = []
    # Nitter RSS: https://nitter.net/search?q=keyword&f=tweets
    url = f"https://nitter.net/search/rss?q={keyword.replace(' ', '+')}&f=tweets"
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:3]:
            # Limpieza básica del contenido
            content = re.sub(r'<.*?>', '', entry.get("description", ""))
            results.append({
                "source": "Twitter (Nitter)",
                "title": entry.title,
                "content": content[:280],
                "link": entry.link,
                "published": entry.get("published", datetime.now().isoformat()),
                "keyword": keyword
            })
    except:
        pass  # Fallback silencioso para MVP
    return results

def fetch_reddit(keyword):
    """Reddit via RSS (sin API key)"""
    results = []
    url = f"https://www.reddit.com/search.rss?q={keyword.replace(' ', '+')}&sort=new"
    feed = feedparser.parse(url)
    for entry in feed.entries[:3]:
        results.append({
            "source": "Reddit",
            "title": entry.title,
            "content": entry.get("summary", ""),
            "link": entry.link,
            "published": entry.get("published", datetime.now().isoformat()),
            "keyword": keyword
        })
    return results

def collect_all(keywords):
    """Orquestador simple"""
    all_posts = []
    for kw in keywords:
        all_posts.extend(fetch_google_alerts([kw]))
        all_posts.extend(fetch_nitter_twitter(kw))
        all_posts.extend(fetch_reddit(kw))
    return all_posts