# main.py

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
import feedparser
import time

# Kullanıcının verdiği kaynaklar
SOURCES = {
    # İngilizce
    'CoinDesk': {'rss_url': 'https://www.coindesk.com/arc/outboundfeeds/rss/', 'lang': 'en'},
    'Cointelegraph EN': {'rss_url': 'https://cointelegraph.com/rss', 'lang': 'en'},
    'Decrypt': {'rss_url': 'https://decrypt.co/feed', 'lang': 'en'},
    'TokenPost': {'rss_url': 'https://www.tokenpost.com/rss', 'lang': 'en'},
    'CryptoNews': {'rss_url': 'https://cryptonews.com/feed/', 'lang': 'en'},
    'Bitcoinist': {'rss_url': 'https://bitcoinist.com/feed/', 'lang': 'en'},
    'NewsBTC': {'rss_url': 'https://www.newsbtc.com/feed/', 'lang': 'en'},
    'Blockchain.News': {'rss_url': 'https://blockchain.news/rss', 'lang': 'en'},
    'CryptoPotato': {'rss_url': 'https://cryptopotato.com/feed/', 'lang': 'en'},
    'CoolWallet': {'rss_url': 'https://www.coolwallet.io/blogs/blog.atom', 'lang': 'en'},
    # Türkçe
    'Cointelegraph TR': {'rss_url': 'https://tr.cointelegraph.com/rss', 'lang': 'tr'},
    'Coin-Turk': {'rss_url': 'https://coin-turk.com/feed/', 'lang': 'tr'},
    'Uzmancoin': {'rss_url': 'https://uzmancoin.com/feed/', 'lang': 'tr'},
    'CoinOtag': {'rss_url': 'https://coinotag.com/feed/', 'lang': 'tr'},
    'Coinkolik': {'rss_url': 'https://www.coinkolik.com/feed/', 'lang': 'tr'},
    'BitcoinSistemi': {'rss_url': 'https://www.bitcoinsistemi.com/feed/', 'lang': 'tr'},
    'Kriptofoni': {'rss_url': 'https://www.kriptofoni.com/feed/', 'lang': 'tr'},
    'Ekoturk': {'rss_url': 'https://www.ekoturk.com/feed/', 'lang': 'tr'},
    'BeInCrypto TR': {'rss_url': 'https://tr.beincrypto.com/feed/', 'lang': 'tr'},
}

# Basit bir cache mekanizması (performans için çok önemli)
# Verileri ve ne zaman çekildiğini saklar
cache = {}
CACHE_DURATION_SECONDS = 600 # 10 dakika

# FastAPI uygulamasını başlat
app = FastAPI(
    title="Crypto News RSS Aggregator API",
    description="Farklı kaynaklardan kripto para haberlerini toplayan basit bir API.",
    version="1.0.0"
)

def fetch_news_from_source(source_name, source_info):
    """Belirtilen bir kaynaktan haberleri çeker ve formatlar."""
    try:
        feed = feedparser.parse(source_info['rss_url'])
        news_items = []
        for entry in feed.entries[:10]: # Her kaynaktan en fazla 10 haber alalım
            news_items.append({
                'source': source_name,
                'title': entry.get('title', 'N/A'),
                'link': entry.get('link', '#'),
                'published': entry.get('published', 'N/A'),
                'summary': entry.get('summary', 'N/A')
            })
        return news_items
    except Exception as e:
        print(f"Hata: {source_name} kaynağından veri çekilemedi - {e}")
        return []

@app.get("/", include_in_schema=False)
def root():
    """Ana sayfayı otomatik olarak API dokümantasyonuna yönlendirir."""
    return RedirectResponse(url="/docs")

@app.get("/news/{lang}", tags=["News"])
def get_news_by_lang(lang: str):
    """
    Belirtilen dildeki (tr, en) veya tüm dillerdeki ('all') haberleri getirir.
    Sonuçlar 10 dakika boyunca önbellekte tutulur.
    """
    if lang not in ['tr', 'en', 'all']:
        raise HTTPException(status_code=400, detail="Geçersiz dil kodu. 'tr', 'en' veya 'all' kullanın.")

    # Cache kontrolü
    cache_key = f"news_{lang}"
    if cache_key in cache and time.time() - cache[cache_key]['timestamp'] < CACHE_DURATION_SECONDS:
        return cache[cache_key]['data']

    all_news = []
    
    # İlgili kaynakları filtrele
    sources_to_fetch = {}
    if lang == 'all':
        sources_to_fetch = SOURCES
    else:
        sources_to_fetch = {name: info for name, info in SOURCES.items() if info['lang'] == lang}

    # Haberleri çek
    for name, info in sources_to_fetch.items():
        all_news.extend(fetch_news_from_source(name, info))
        
    # Haberleri tarihe göre (en yeniden en eskiye) sırala (best-effort)
    try:
        # feedparser tarih formatlarını ayrıştırmaya çalışır, biz de sıralarız
        all_news.sort(key=lambda x: feedparser._parse_date(x['published']) if x['published'] != 'N/A' else (0,), reverse=True)
    except Exception:
        # Tarih formatları uyumsuzsa sıralama yapmadan devam et
        pass

    # Cache'e kaydet
    cache[cache_key] = {
        'timestamp': time.time(),
        'data': all_news
    }

    return all_news