import feedparser
import httpx
import logging
import hashlib
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from app.database import DBContext

logger = logging.getLogger("macro.news")

RSS_FEEDS = [
    # Indonesia Feeds
    {
        "name": "CNBC Indonesia (Market & Makro)",
        "url": "https://www.cnbcindonesia.com/market/rss",
        "region": "Indonesia",
        "default_cat": "Pasar Modal & Makro"
    },
    {
        "name": "Antara News (Ekonomi)",
        "url": "https://www.antaranews.com/rss/ekonomi.xml",
        "region": "Indonesia",
        "default_cat": "Fiskal & Kebijakan"
    },
    {
        "name": "Kontan (Makro & Finansial)",
        "url": "https://nasional.kontan.co.id/rss",
        "region": "Indonesia",
        "default_cat": "Makroekonomi Umum"
    },
    {
        "name": "CNBC Indonesia (Ekonomi Makro)",
        "url": "https://www.cnbcindonesia.com/news/rss",
        "region": "Indonesia",
        "default_cat": "Kebijakan Moneter"
    },
    # Global Feeds
    {
        "name": "US Federal Reserve",
        "url": "https://www.federalreserve.gov/feeds/press_all.xml",
        "region": "Global",
        "default_cat": "Kebijakan Moneter"
    },
    {
        "name": "CNBC World Economy",
        "url": "https://www.cnbc.com/id/20910258/device/rss/rss.html",
        "region": "Global",
        "default_cat": "Ekonomi Global"
    },
    {
        "name": "BBC Business & Economy",
        "url": "http://feeds.bbci.co.uk/news/business/rss.xml",
        "region": "Global",
        "default_cat": "Perdagangan Global"
    },
    {
        "name": "MarketWatch Macro",
        "url": "https://feeds.content.dowjones.io/public/rss/mw_topstories",
        "region": "Global",
        "default_cat": "Pasar & Finansial"
    },
    {
        "name": "Yahoo Finance World",
        "url": "https://finance.yahoo.com/news/rssindex",
        "region": "Global",
        "default_cat": "Ekonomi Global"
    }
]

def clean_html(text):
    if not text:
        return ""
    soup = BeautifulSoup(text, "html.parser")
    clean = soup.get_text(separator=" ", strip=True)
    return clean[:400] + ("..." if len(clean) > 400 else "")

def classify_news(title, summary):
    content = (title + " " + (summary or "")).lower()
    
    # 1. Category Classification
    category = "Makroekonomi Umum"
    if any(k in content for k in ["suku bunga", "bi-rate", "fed", "fomc", "rdg", "moneter", "central bank", "powell", "interest rate"]):
        category = "Kebijakan Moneter"
    elif any(k in content for k in ["inflasi", "cpi", "deflasi", "pdb", "gdp", "pertumbuhan ekonomi", "konsumsi", "bps"]):
        category = "Inflasi & Pertumbuhan"
    elif any(k in content for k in ["rupiah", "dollar", "dolar", "kurs", "dxy", "valas", "sbn", "obligasi", "yield", "treasury"]):
        category = "Valas & Obligasi"
    elif any(k in content for k in ["minyak", "oil", "brent", "wti", "emas", "gold", "cpo", "sawit", "batubara", "coal", "komoditas"]):
        category = "Komoditas & Energi"
    elif any(k in content for k in ["apbn", "pajak", "fiskal", "kemenkeu", "sri mulyani", "anggaran", "surplus", "defisit", "ekspor", "impor", "neraca dagang", "tarif", "trade"]):
        category = "Fiskal & Perdagangan"
    elif any(k in content for k in ["ihsg", "saham", "bursa", "indeks", "wall street", "nasdaq", "emiten"]):
        category = "Pasar Modal"

    # 2. Sentiment Classification
    sentiment = "Netral"
    if any(k in content for k in ["hawkish", "naikkan bunga", "inflasi melonjak", "hike", "pengetatan"]):
        sentiment = "Hawkish"
    elif any(k in content for k in ["dovish", "pangkas bunga", "potong suku bunga", "rate cut", "pelonggaran", "stimulus"]):
        sentiment = "Dovish"
    elif any(k in content for k in ["surplus", "menguat", "rekor", "bullish", "tumbuh pesat", "optimis", "ekspansi"]):
        sentiment = "Bullish"
    elif any(k in content for k in ["merosot", "anjlok", "melemah", "bearish", "resesi", "koreksi", "tekanan", "perang dagang", "ancaman"]):
        sentiment = "Bearish"

    # 3. Tags
    tags = []
    if "bi" in content or "bank indonesia" in content: tags.append("Bank Indonesia")
    if "the fed" in content or "powell" in content or "fomc" in content: tags.append("The Fed")
    if "rupiah" in content: tags.append("Rupiah")
    if "ihsg" in content: tags.append("IHSG")
    if "inflasi" in content or "cpi" in content: tags.append("Inflasi")
    if "minyak" in content or "oil" in content: tags.append("Minyak")
    if "emas" in content or "gold" in content: tags.append("Emas")
    if "sawit" in content or "cpo" in content: tags.append("CPO")
    if "batubara" in content or "coal" in content: tags.append("Batubara")
    if "china" in content or "tiongkok" in content: tags.append("China")
    if "amerika" in content or "us" in content or "u.s." in content: tags.append("AS")

    return category, sentiment, ",".join(tags)

def sync_rss_news():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    total_added = 0
    now_iso = datetime.now(timezone.utc).isoformat()
    
    with DBContext(commit=True) as cursor:
        for feed_info in RSS_FEEDS:
            try:
                feed = feedparser.parse(feed_info["url"], request_headers=headers)
                for entry in feed.entries[:25]:  # Take top 25 latest per feed
                    title = entry.get("title", "").strip()
                    if not title:
                        continue
                    
                    link = entry.get("link", "")
                    raw_summary = entry.get("summary", "") or entry.get("description", "")
                    clean_desc = clean_html(raw_summary)
                    
                    # Published date parsing
                    pub_date = entry.get("published", "") or entry.get("pubDate", "") or now_iso
                    
                    # Guid or hash
                    guid = entry.get("id") or entry.get("guid") or hashlib.md5((link + title).encode("utf-8")).hexdigest()
                    
                    cat, sentiment, tags = classify_news(title, clean_desc)
                    if cat == "Makroekonomi Umum" and feed_info.get("default_cat"):
                        cat = feed_info["default_cat"]
                        
                    cursor.execute("""
                    INSERT INTO macro.news (id, title, link, summary, source, region, category, sentiment, published_at, created_at, tags)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT(link) DO UPDATE SET
                        summary = EXCLUDED.summary,
                        category = EXCLUDED.category,
                        sentiment = EXCLUDED.sentiment
                    """, (
                        guid, title, link, clean_desc, feed_info["name"],
                        feed_info["region"], cat, sentiment, pub_date, now_iso, tags
                    ))
                    total_added += 1
            except Exception as e:
                logger.warning(f"Error reading feed {feed_info['name']}: {e}")
                
    logger.info(f"News synchronization complete with PostgreSQL. Ingested/updated {total_added} articles.")
    return total_added

if __name__ == "__main__":
    from app.database import init_db
    init_db()
    count = sync_rss_news()
    print(f"Successfully processed {count} news items.")
