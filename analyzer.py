# analyzer.py
from transformers import pipeline
import re

# Cargar modelo gratuito de Hugging Face (se cachea localmente)
# Modelo multilingüe ligero para sentiment analysis
try:
    sentiment_pipeline = pipeline(
        "sentiment-analysis",
        model="cardiffnlp/twitter-xlm-roberta-base-sentiment",
        framework="pt"
    )
except:
    # Fallback si no descarga: análisis heurístico simple
    sentiment_pipeline = None

def analyze_sentiment_heuristic(text):
    """Fallback: reglas simples en español/inglés"""
    text_lower = text.lower()
    positive_words = ['excelente', 'increíble', 'éxito', 'impacto', 'innovación', 'great', 'success', 'impactful']
    negative_words = ['problema', 'fracaso', 'crítica', 'difícil', 'fail', 'problem', 'critic']
    
    pos_count = sum(1 for w in positive_words if w in text_lower)
    neg_count = sum(1 for w in negative_words if w in text_lower)
    
    if pos_count > neg_count:
        return "positive", 0.7
    elif neg_count > pos_count:
        return "negative", 0.6
    else:
        return "neutral", 0.5

def analyze_post(post_content):
    """Analiza sentimiento y relevancia"""
    # Sentiment con HF o fallback
    if sentiment_pipeline and len(post_content) < 512:
        try:
            result = sentiment_pipeline(post_content[:512])[0]
            sentiment = result['label'].lower().replace('star', '')  # LABEL_0 -> neutral, etc.
            confidence = result['score']
        except:
            sentiment, confidence = analyze_sentiment_heuristic(post_content)
    else:
        sentiment, confidence = analyze_sentiment_heuristic(post_content)
    
    # Relevancia para grassroots (heurística simple)
    grassroots_keywords = ['comunidad', 'local', 'base', 'grassroots', 'territorio', 'organizaciones', 'community', 'local', 'grassroots']
    relevance_score = min(10, sum(2 for kw in grassroots_keywords if kw.lower() in post_content.lower()) + 3)
    
    # Insight accionable (regla simple)
    actionable = None
    if 'necesita' in post_content.lower() or 'need' in post_content.lower():
        actionable = "Posible oportunidad de apoyo o colaboración"
    elif 'éxito' in post_content.lower() or 'success' in post_content.lower():
        actionable = "Caso de éxito para escalar o documentar"
    
    return {
        "sentiment": sentiment,
        "confidence": round(confidence, 2),
        "relevance_to_grassroots": relevance_score,
        "actionable_insight": actionable
    }