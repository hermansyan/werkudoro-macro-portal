import httpx
import logging
from datetime import datetime, timezone
import json
from app.database import DBContext

logger = logging.getLogger("macro.indicators")

YAHOO_SYMBOLS = {
    "USD_IDR": {"symbol": "IDR=X", "name": "Kurs USD / IDR", "cat": "Valas & Kurs", "region": "Indonesia", "unit": "IDR", "desc": "Kurs transaksi Dolar AS terhadap Rupiah"},
    "IHSG": {"symbol": "^JKSE", "name": "IHSG (Indeks Saham Gabungan)", "cat": "Pasar Modal", "region": "Indonesia", "unit": "Pts", "desc": "Indeks acuan pasar saham Bursa Efek Indonesia"},
    "US_10Y": {"symbol": "^TNX", "name": "US 10-Year Treasury Yield", "cat": "Obligasi", "region": "Amerika Serikat", "unit": "%", "desc": "Imbal hasil obligasi pemerintah AS tenor 10 tahun"},
    "US_30Y": {"symbol": "^TYX", "name": "US 30-Year Treasury Yield", "cat": "Obligasi", "region": "Amerika Serikat", "unit": "%", "desc": "Imbal hasil obligasi pemerintah AS tenor jangka panjang 30 tahun"},
    "US_3M": {"symbol": "^IRX", "name": "US 3-Month T-Bill Yield", "cat": "Obligasi", "region": "Amerika Serikat", "unit": "%", "desc": "Imbal hasil Treasury Bill AS tenor jangka pendek 3 bulan"},
    "VIX": {"symbol": "^VIX", "name": "CBOE Volatility Index (VIX)", "cat": "Volatilitas & Risiko", "region": "Global", "unit": "Pts", "desc": "Indeks volatilitas pasar dan ketakutan investor ekuitas global (Fear Index)"},
    "DXY": {"symbol": "DX-Y.NYB", "name": "US Dollar Index (DXY)", "cat": "Valas & Kurs", "region": "Amerika Serikat", "unit": "Pts", "desc": "Indeks kekuatan Dolar AS terhadap 6 mata uang utama"},
    "BRENT_OIL": {"symbol": "BZ=F", "name": "Minyak Mentah Brent", "cat": "Komoditas", "region": "Komoditas", "unit": "USD/bbl", "desc": "Harga acuan minyak mentah global Brent Crude"},
    "WTI_OIL": {"symbol": "CL=F", "name": "Minyak Mentah WTI", "cat": "Komoditas", "region": "Komoditas", "unit": "USD/bbl", "desc": "Harga acuan minyak mentah West Texas Intermediate"},
    "NATURAL_GAS": {"symbol": "NG=F", "name": "Gas Alam (Natural Gas)", "cat": "Komoditas", "region": "Komoditas", "unit": "USD/MMBtu", "desc": "Harga kontrak berjangka gas alam internasional"},
    "GOLD": {"symbol": "GC=F", "name": "Emas Spot Dunia (Gold)", "cat": "Komoditas", "region": "Komoditas", "unit": "USD/toz", "desc": "Harga spot emas internasional per troy ounce"},
    "BTC_USD": {"symbol": "BTC-USD", "name": "Bitcoin / USD", "cat": "Likuiditas Global", "region": "Global", "unit": "USD", "desc": "Aset digital barometer selera risiko (risk appetite) & likuiditas global"},
    "ETH_USD": {"symbol": "ETH-USD", "name": "Ethereum / USD", "cat": "Likuiditas Global", "region": "Global", "unit": "USD", "desc": "Aset smart contract & proxy likuiditas / risk-on global"},
    "US_TIPS_10Y": {"symbol": "TIP", "name": "iShares TIPS Bond ETF", "cat": "Obligasi", "region": "Amerika Serikat", "unit": "USD", "desc": "Proxy instrumen Treasury Inflation-Protected Securities (Real Yields)"},
    "USD_JPY": {"symbol": "JPY=X", "name": "Kurs USD / JPY", "cat": "Valas & Kurs", "region": "Jepang", "unit": "JPY", "desc": "Nilai tukar Dolar AS terhadap Yen Jepang"},
    "GBP_USD": {"symbol": "GBPUSD=X", "name": "Kurs GBP / USD", "cat": "Valas & Kurs", "region": "Inggris", "unit": "USD", "desc": "Nilai tukar Poundsterling terhadap Dolar AS"},
    "USD_CNY": {"symbol": "CNY=X", "name": "Kurs USD / CNY", "cat": "Valas & Kurs", "region": "China", "unit": "CNY", "desc": "Nilai tukar Dolar AS terhadap Yuan China"},
    "COPPER": {"symbol": "HG=F", "name": "Tembaga Dunia (Copper)", "cat": "Komoditas", "region": "Komoditas", "unit": "USD/lb", "desc": "Harga kontrak tembaga acuan industri manufaktur global"}
}

BENCHMARK_INDICATORS = [
    # --- INDONESIA ---
    {
        "key": "BI_RATE",
        "name": "BI-Rate (Suku Bunga Acuan BI)",
        "category": "Kebijakan Moneter",
        "region": "Indonesia",
        "value": 6.00,
        "prev_value": 6.25,
        "unit": "%",
        "change_pct": -0.25,
        "trend": "down",
        "source": "Bank Indonesia",
        "description": "Suku bunga acuan Bank Indonesia untuk stabilitas moneter & inflasi"
    },
    {
        "key": "INFLASI_INDO",
        "name": "Inflasi Indonesia (CPI YoY)",
        "category": "Inflasi",
        "region": "Indonesia",
        "value": 1.71,
        "prev_value": 2.12,
        "unit": "% YoY",
        "change_pct": -0.41,
        "trend": "down",
        "source": "BPS (Badan Pusat Statistik)",
        "description": "Laju inflasi tahun ke tahun, dalam rentang target BI 1.5% - 3.5%"
    },
    {
        "key": "GDP_INDO",
        "name": "Pertumbuhan PDB Indonesia",
        "category": "Pertumbuhan Ekonomi",
        "region": "Indonesia",
        "value": 5.05,
        "prev_value": 5.11,
        "unit": "% YoY",
        "change_pct": -0.06,
        "trend": "neutral",
        "source": "BPS",
        "description": "Pertumbuhan Produk Domestik Bruto tahunan Indonesia"
    },
    {
        "key": "CADANGAN_DEVISA",
        "name": "Cadangan Devisa RI",
        "category": "Cadangan Devisa",
        "region": "Indonesia",
        "value": 150.2,
        "prev_value": 149.9,
        "unit": "Miliar USD",
        "change_pct": 0.20,
        "trend": "up",
        "source": "Bank Indonesia",
        "description": "Posisi cadangan devisa setara pembiayaan 6.5 bulan impor"
    },
    {
        "key": "NERACA_DAGANG",
        "name": "Neraca Perdagangan RI",
        "category": "Perdagangan",
        "region": "Indonesia",
        "value": 2.47,
        "prev_value": 2.15,
        "unit": "Miliar USD",
        "change_pct": 14.88,
        "trend": "up",
        "source": "BPS / Kemendag",
        "description": "Surplus neraca perdagangan bulanan Indonesia berturut-turut"
    },
    {
        "key": "SBN_10Y",
        "name": "Yield SBN 10 Tahun (ID10YT)",
        "category": "Obligasi",
        "region": "Indonesia",
        "value": 6.85,
        "prev_value": 6.78,
        "unit": "%",
        "change_pct": 0.07,
        "trend": "up",
        "source": "PHEI / DJPPR Kemenkeu",
        "description": "Yield Surat Berharga Negara tenor acuan 10 tahun"
    },
    {
        "key": "SRBI_12M",
        "name": "Suku Bunga SRBI 12 Bulan",
        "category": "Instrumen Moneter",
        "region": "Indonesia",
        "value": 7.15,
        "prev_value": 7.22,
        "unit": "%",
        "change_pct": -0.07,
        "trend": "down",
        "source": "Bank Indonesia",
        "description": "Sekuritas Rupiah Bank Indonesia tenor 12 bulan penyerap likuiditas asing"
    },
    {
        "key": "APBN_DEFICIT",
        "name": "Keseimbangan Primer APBN",
        "category": "Fiskal",
        "region": "Indonesia",
        "value": -2.29,
        "prev_value": -2.38,
        "unit": "% PDB",
        "change_pct": 0.09,
        "trend": "up",
        "source": "Kemenkeu RI",
        "description": "Rasio defisit fiskal APBN terhadap Produk Domestik Bruto"
    },

    # --- NEGARA MAJU: AMERIKA SERIKAT ---
    {
        "key": "FED_FUNDS_RATE",
        "name": "US Fed Funds Rate (FFR)",
        "category": "Kebijakan Moneter",
        "region": "Amerika Serikat",
        "value": 4.50,
        "prev_value": 4.75,
        "unit": "%",
        "change_pct": -0.25,
        "trend": "down",
        "source": "Federal Reserve (The Fed)",
        "description": "Target suku bunga acuan bank sentral Amerika Serikat"
    },
    {
        "key": "US_CPI",
        "name": "Inflasi AS (US CPI YoY)",
        "category": "Inflasi",
        "region": "Amerika Serikat",
        "value": 2.70,
        "prev_value": 2.60,
        "unit": "% YoY",
        "change_pct": 0.10,
        "trend": "up",
        "source": "US Bureau of Labor Statistics",
        "description": "Indeks Harga Konsumen Amerika Serikat tahunan"
    },
    {
        "key": "US_GDP",
        "name": "Pertumbuhan PDB AS (GDP YoY)",
        "category": "Pertumbuhan Ekonomi",
        "region": "Amerika Serikat",
        "value": 2.80,
        "prev_value": 3.00,
        "unit": "% YoY",
        "change_pct": -0.20,
        "trend": "down",
        "source": "US Bureau of Economic Analysis",
        "description": "Laju pertumbuhan Produk Domestik Bruto riil Amerika Serikat"
    },
    {
        "key": "US_UNEMP",
        "name": "Tingkat Pengangguran AS",
        "category": "Ketenagakerjaan",
        "region": "Amerika Serikat",
        "value": 4.10,
        "prev_value": 4.10,
        "unit": "%",
        "change_pct": 0.00,
        "trend": "neutral",
        "source": "US BLS",
        "description": "Non-Farm Payrolls unemployment rate"
    },

    # --- NEGARA MAJU: KAWASAN EURO (EUROZONE) ---
    {
        "key": "ECB_RATE",
        "name": "ECB Deposit Facility Rate",
        "category": "Kebijakan Moneter",
        "region": "Kawasan Euro",
        "value": 3.25,
        "prev_value": 3.50,
        "unit": "%",
        "change_pct": -0.25,
        "trend": "down",
        "source": "European Central Bank",
        "description": "Suku bunga acuan utama bank sentral kawasan Euro"
    },
    {
        "key": "EU_HICP",
        "name": "Inflasi Eurozone (HICP YoY)",
        "category": "Inflasi",
        "region": "Kawasan Euro",
        "value": 2.00,
        "prev_value": 1.70,
        "unit": "% YoY",
        "change_pct": 0.30,
        "trend": "up",
        "source": "Eurostat",
        "description": "Harmonised Index of Consumer Prices Kawasan Euro"
    },
    {
        "key": "EU_GDP",
        "name": "Pertumbuhan PDB Eurozone",
        "category": "Pertumbuhan Ekonomi",
        "region": "Kawasan Euro",
        "value": 0.90,
        "prev_value": 0.60,
        "unit": "% YoY",
        "change_pct": 0.30,
        "trend": "up",
        "source": "Eurostat",
        "description": "Pertumbuhan ekonomi gabungan negara anggota zona Euro"
    },
    {
        "key": "GER_10Y",
        "name": "Yield Bund Jerman 10Y",
        "category": "Obligasi",
        "region": "Kawasan Euro",
        "value": 2.35,
        "prev_value": 2.28,
        "unit": "%",
        "change_pct": 0.07,
        "trend": "up",
        "source": "Deutsche Bundesbank",
        "description": "Benchmark surat utang pemerintah Jerman tenor 10 tahun"
    },

    # --- NEGARA MAJU: JEPANG ---
    {
        "key": "BOJ_RATE",
        "name": "Bank of Japan Policy Rate",
        "category": "Kebijakan Moneter",
        "region": "Jepang",
        "value": 0.25,
        "prev_value": 0.10,
        "unit": "%",
        "change_pct": 0.15,
        "trend": "up",
        "source": "Bank of Japan (BoJ)",
        "description": "Suku bunga acuan uncollateralized overnight call rate BoJ"
    },
    {
        "key": "JP_CPI",
        "name": "Inflasi Jepang (Core CPI YoY)",
        "category": "Inflasi",
        "region": "Jepang",
        "value": 2.50,
        "prev_value": 2.40,
        "unit": "% YoY",
        "change_pct": 0.10,
        "trend": "up",
        "source": "Statistics Bureau Japan",
        "description": "Inflasi inti konsumen Jepang melampaui target 2% BoJ"
    },
    {
        "key": "JP_GDP",
        "name": "Pertumbuhan PDB Jepang",
        "category": "Pertumbuhan Ekonomi",
        "region": "Jepang",
        "value": 0.30,
        "prev_value": -0.50,
        "unit": "% YoY",
        "change_pct": 0.80,
        "trend": "up",
        "source": "Cabinet Office Japan",
        "description": "Pemulihan pertumbuhan ekonomi kuartalan Jepang"
    },
    {
        "key": "JGB_10Y",
        "name": "Yield JGB Jepang 10Y",
        "category": "Obligasi",
        "region": "Jepang",
        "value": 0.95,
        "prev_value": 0.92,
        "unit": "%",
        "change_pct": 0.03,
        "trend": "up",
        "source": "Ministry of Finance Japan",
        "description": "Yield obligasi pemerintah Jepang tenor 10 tahun"
    },

    # --- NEGARA MAJU: INGGRIS (UK) ---
    {
        "key": "BOE_RATE",
        "name": "BoE Official Bank Rate",
        "category": "Kebijakan Moneter",
        "region": "Inggris",
        "value": 4.75,
        "prev_value": 5.00,
        "unit": "%",
        "change_pct": -0.25,
        "trend": "down",
        "source": "Bank of England",
        "description": "Suku bunga acuan kebijakan moneter Inggris"
    },
    {
        "key": "UK_CPI",
        "name": "Inflasi Inggris (UK CPI YoY)",
        "category": "Inflasi",
        "region": "Inggris",
        "value": 2.30,
        "prev_value": 1.70,
        "unit": "% YoY",
        "change_pct": 0.60,
        "trend": "up",
        "source": "Office for National Statistics",
        "description": "Indeks Harga Konsumen Inggris tahunan"
    },
    {
        "key": "UK_10Y",
        "name": "Yield Gilt Inggris 10Y",
        "category": "Obligasi",
        "region": "Inggris",
        "value": 4.25,
        "prev_value": 4.15,
        "unit": "%",
        "change_pct": 0.10,
        "trend": "up",
        "source": "UK Debt Management Office",
        "description": "Yield obligasi pemerintah Inggris (Gilts) tenor 10 tahun"
    },

    # --- NEGARA MAJU / MITRA UTAMA: CHINA ---
    {
        "key": "PBOC_LPR_1Y",
        "name": "PBoC Loan Prime Rate 1Y",
        "category": "Kebijakan Moneter",
        "region": "China",
        "value": 3.10,
        "prev_value": 3.35,
        "unit": "%",
        "change_pct": -0.25,
        "trend": "down",
        "source": "People's Bank of China",
        "description": "Suku bunga pinjaman acuan perbankan komersial China"
    },
    {
        "key": "CHINA_GDP",
        "name": "Pertumbuhan PDB China",
        "category": "Pertumbuhan Ekonomi",
        "region": "China",
        "value": 4.80,
        "prev_value": 4.70,
        "unit": "% YoY",
        "change_pct": 0.10,
        "trend": "up",
        "source": "National Bureau of Statistics China",
        "description": "Pertumbuhan ekonomi mitra dagang terbesar Indonesia"
    },
    {
        "key": "CHINA_CPI",
        "name": "Inflasi China (CPI YoY)",
        "category": "Inflasi",
        "region": "China",
        "value": 0.30,
        "prev_value": 0.40,
        "unit": "% YoY",
        "change_pct": -0.10,
        "trend": "down",
        "source": "NBS China",
        "description": "Tingkat inflasi rendah mencerminkan kehati-hatian konsumsi domestik"
    },
    {
        "key": "CHINA_10Y",
        "name": "Yield Obligasi China 10Y",
        "category": "Obligasi",
        "region": "China",
        "value": 2.12,
        "prev_value": 2.15,
        "unit": "%",
        "change_pct": -0.03,
        "trend": "down",
        "source": "China Central Depository & Clearing",
        "description": "Yield obligasi negara China tenor 10 tahun"
    },

    # --- KOMODITAS & ENERGI ---
    {
        "key": "CPO_PRICE",
        "name": "Minyak Kelapa Sawit (CPO)",
        "category": "Komoditas",
        "region": "Komoditas",
        "value": 4350.0,
        "prev_value": 4280.0,
        "unit": "MYR/Ton",
        "change_pct": 1.63,
        "trend": "up",
        "source": "Bursa Malaysia Derivatives",
        "description": "Harga kontrak berjangka CPO komoditas ekspor andalan Indonesia"
    },
    {
        "key": "COAL_PRICE",
        "name": "Batubara Newcastle (Coal)",
        "category": "Komoditas",
        "region": "Komoditas",
        "value": 138.5,
        "prev_value": 141.2,
        "unit": "USD/Ton",
        "change_pct": -1.91,
        "trend": "down",
        "source": "Newcastle GlobalCOAL",
        "description": "Harga patokan ekspor batubara termal kalori tinggi"
    },
    {
        "key": "NICKEL_PRICE",
        "name": "Nikel LME (Nickel)",
        "category": "Komoditas",
        "region": "Komoditas",
        "value": 15850.0,
        "prev_value": 15600.0,
        "unit": "USD/Ton",
        "change_pct": 1.60,
        "trend": "up",
        "source": "London Metal Exchange",
        "description": "Harga spot nikel murni untuk hilirisasi baterai & stainless steel"
    }
]

def fetch_live_market_data():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    results = {}
    
    with httpx.Client(timeout=10, headers=headers) as client:
        for key, meta in YAHOO_SYMBOLS.items():
            sym = meta["symbol"]
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=5d"
            try:
                r = client.get(url)
                if r.status_code == 200:
                    data = r.json()
                    res = data.get("chart", {}).get("result", [])
                    if res:
                        m = res[0].get("meta", {})
                        price = m.get("regularMarketPrice")
                        prev = m.get("chartPreviousClose")
                        if price is not None:
                            chg = ((price - prev) / prev * 100) if (prev and prev > 0) else 0.0
                            trend = "up" if chg > 0.05 else ("down" if chg < -0.05 else "neutral")
                            results[key] = {
                                "key": key,
                                "name": meta["name"],
                                "category": meta["cat"],
                                "region": meta["region"],
                                "value": round(float(price), 2),
                                "prev_value": round(float(prev), 2) if prev else round(float(price), 2),
                                "unit": meta["unit"],
                                "change_pct": round(float(chg), 2),
                                "trend": trend,
                                "source": "Market Live (Yahoo Finance)",
                                "description": meta["desc"]
                            }
            except Exception as e:
                logger.warning(f"Failed to fetch market data for {sym}: {e}")
                
    return results

def sync_indicators():
    now_iso = datetime.now(timezone.utc).isoformat()
    
    with DBContext(commit=True) as cursor:
        # 1. Store/update benchmark indicators
        for item in BENCHMARK_INDICATORS:
            cursor.execute("""
            INSERT INTO macro.indicators (key, name, category, region, value, prev_value, unit, change_pct, trend, last_updated, source, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT(key) DO UPDATE SET
                name = EXCLUDED.name,
                category = EXCLUDED.category,
                region = EXCLUDED.region,
                value = EXCLUDED.value,
                prev_value = EXCLUDED.prev_value,
                unit = EXCLUDED.unit,
                change_pct = EXCLUDED.change_pct,
                trend = EXCLUDED.trend,
                last_updated = EXCLUDED.last_updated,
                source = EXCLUDED.source,
                description = EXCLUDED.description
            """, (
                item["key"], item["name"], item["category"], item["region"],
                item["value"], item["prev_value"], item["unit"], item["change_pct"],
                item["trend"], now_iso, item["source"], item["description"]
            ))
            
        # 2. Fetch & update live market indicators
        live_data = fetch_live_market_data()
        for key, item in live_data.items():
            cursor.execute("""
            INSERT INTO macro.indicators (key, name, category, region, value, prev_value, unit, change_pct, trend, last_updated, source, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT(key) DO UPDATE SET
                name = EXCLUDED.name,
                category = EXCLUDED.category,
                region = EXCLUDED.region,
                value = EXCLUDED.value,
                prev_value = EXCLUDED.prev_value,
                unit = EXCLUDED.unit,
                change_pct = EXCLUDED.change_pct,
                trend = EXCLUDED.trend,
                last_updated = EXCLUDED.last_updated,
                source = EXCLUDED.source,
                description = EXCLUDED.description
            """, (
                item["key"], item["name"], item["category"], item["region"],
                item["value"], item["prev_value"], item["unit"], item["change_pct"],
                item["trend"], now_iso, item["source"], item["description"]
            ))
            
    logger.info("Macro indicators synchronized successfully with PostgreSQL.")
    return len(BENCHMARK_INDICATORS) + len(live_data)

if __name__ == "__main__":
    from app.database import init_db
    init_db()
    count = sync_indicators()
    print(f"Synced {count} indicators.")
